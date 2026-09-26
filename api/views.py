"""
JSON API для Telegram Mini App.

Авторизація — підписаний initData (заголовок X-Telegram-Init-Data), не cookies,
тому CSRF тут не застосовується (csrf_exempt). Усі перевірки лімітів
дублюються на сервері — клієнтський календар лише підказує.
"""

import json
from collections import Counter
from datetime import date

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from api.auth import telegram_auth
from core import services
from core import sick_leave_files
from core.models import (
    AbsenceRequest,
    Project,
    Region,
    RequestDepartment,
    RequestStatus,
    RequestType,
    ServiceRequest,
    SickLeaveDocument,
)
from users.models import Language, User

MAX_SERVICE_TEXT = 2000


def _body(request) -> dict:
    try:
        return json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _error(code: str, status: int = 400, **detail):
    return JsonResponse({"error": code, "detail": detail}, status=status)


def _user_payload(user: User) -> dict:
    return {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language": user.language,
        "is_staff": user.is_staff,
    }


def _absence_payload(req: AbsenceRequest, with_worker: bool = False) -> dict:
    data = {
        "id": req.id,
        "kind": "absence",
        "type": req.request_type,
        "status": req.status,
        "project": req.project.name,
        "region": req.project.region.name,
        "start": req.start_date.isoformat(),
        "end": req.end_date.isoformat(),
        "days": req.days_count,
        "dates": [d.isoformat() for d in services.request_dates(req)],
        "created_at": req.created_at.isoformat(),
    }
    if req.request_type == RequestType.L4:
        documents = [_document_payload(doc) for doc in req.documents.all()]
        data["documents"] = documents
        data["needs_document"] = not documents
    if with_worker:
        data["worker"] = {
            "name": f"{req.user.last_name} {req.user.first_name}".strip(),
            "phone": req.user.phone,
        }
        data["can_reject"] = req.can_be_rejected()
    return data


def _document_payload(doc: SickLeaveDocument) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "size": doc.size,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "emailed_at": doc.emailed_at.isoformat() if doc.emailed_at else None,
    }


def _service_payload(req: ServiceRequest) -> dict:
    return {
        "id": req.id,
        "kind": "service",
        "type": req.request_type,
        "status": req.status,
        "text": req.text,
        "created_at": req.created_at.isoformat(),
    }


# --- Профіль ---------------------------------------------------------------


@require_GET
@telegram_auth(require_access=False)
def me(request):
    user = request.app_user
    return JsonResponse(
        {
            "telegram_id": request.tg_user["id"],
            "access": user is not None,
            "user": _user_payload(user) if user else None,
        }
    )


@csrf_exempt
@require_POST
@telegram_auth()
def set_language(request):
    language = _body(request).get("language")
    if language not in Language.values:
        return _error("bad_language")
    request.app_user.language = language
    request.app_user.save(update_fields=["language"])
    return JsonResponse({"language": language})


# --- Довідники --------------------------------------------------------------


@require_GET
@telegram_auth()
def regions(request):
    data = []
    for region in Region.objects.prefetch_related("projects").order_by("name"):
        projects = [
            {"id": p.id, "name": p.name} for p in region.projects.all().order_by("name")
        ]
        if projects:
            data.append({"id": region.id, "name": region.name, "projects": projects})
    return JsonResponse({"regions": data})


@require_GET
@telegram_auth()
def coordinators(request):
    data = []
    for region in Region.objects.order_by("name"):
        people = (
            User.objects.filter(
                is_staff=True, is_active=True, coordinated_projects__region=region
            )
            .distinct()
            .order_by("last_name", "first_name")
        )
        if people:
            data.append(
                {
                    "region": region.name,
                    "people": [
                        {
                            "name": f"{u.last_name} {u.first_name}".strip(),
                            "phone": u.phone,
                            "email": u.email or "",
                        }
                        for u in people
                    ],
                }
            )
    return JsonResponse({"regions": data})


# --- Календар і вихідні/L4 --------------------------------------------------


@require_GET
@telegram_auth()
def project_calendar(request, project_id: int):
    project = Project.objects.filter(id=project_id).first()
    if project is None:
        return _error("project_not_found", 404)

    request_type = request.GET.get("type", RequestType.DAYOFF)
    today = timezone.localdate()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        start, end = services.month_bounds(year, month)
    except ValueError:
        return _error("bad_month")

    mine = services.user_dates(request.app_user.id, project.id, start, end)
    is_dayoff = request_type == RequestType.DAYOFF
    taken = services.occupancy(project.id, start, end) if is_dayoff else {}
    capacity = services.capacity_by_date(project, start, end) if is_dayoff else {}

    days = []
    for day_number in range(1, end.day + 1):
        d = date(year, month, day_number)
        if d < today:
            state = "past"
        elif d in mine:
            state = "mine"
        elif (
            is_dayoff
            and capacity[d] is not None
            and len(taken.get(d, ())) >= capacity[d]
        ):
            state = "full"
        else:
            state = "free"
        days.append({"date": d.isoformat(), "state": state})

    return JsonResponse(
        {
            "year": year,
            "month": month,
            "today": today.isoformat(),
            "limit": project.dayoff_limit if is_dayoff else services.L4_MAX_DAYS,
            "limit_scope": "month" if is_dayoff else "request",
            "used_in_month": (
                sum(1 for kind in mine.values() if kind == RequestType.DAYOFF)
                if is_dayoff
                else 0
            ),
            "days": days,
        }
    )


@csrf_exempt
@require_POST
@telegram_auth()
def create_absence_request(request):
    payload = _body(request)
    request_type = payload.get("type")
    if request_type not in (RequestType.DAYOFF, RequestType.L4):
        return _error("bad_type")

    try:
        dates = sorted(
            {date.fromisoformat(value) for value in payload.get("dates", [])}
        )
    except (TypeError, ValueError):
        return _error("bad_dates")
    if not dates:
        return _error("no_dates")

    user = request.app_user
    today = timezone.localdate()
    if dates[0] < today:
        return _error("past_date", date=dates[0].isoformat())
    if request_type == RequestType.L4 and len(dates) > services.L4_MAX_DAYS:
        return _error("l4_limit", limit=services.L4_MAX_DAYS)

    try:
        project_id = int(payload.get("project_id"))
    except (TypeError, ValueError):
        return _error("project_not_found", 404)

    with transaction.atomic():
        # Блокування рядка проєкту серіалізує одночасні подання в один проєкт,
        # щоб два працівники не зайняли останнє вільне місце на дату одночасно.
        project = Project.objects.select_for_update().filter(id=project_id).first()
        if project is None:
            return _error("project_not_found", 404)

        existing = services.user_dates(user.id, project.id, dates[0], dates[-1])
        overlap = [d.isoformat() for d in dates if d in existing]
        if overlap:
            return _error("already_requested", dates=overlap)

        if request_type == RequestType.DAYOFF:
            for (year, month), count in Counter(
                (d.year, d.month) for d in dates
            ).items():
                used = services.used_dayoff_in_month(user.id, project.id, year, month)
                if used + count > project.dayoff_limit:
                    return _error(
                        "month_limit",
                        limit=project.dayoff_limit,
                        used=used,
                        month=f"{month:02d}.{year}",
                    )

            taken = services.occupancy(project.id, dates[0], dates[-1])
            capacity = services.capacity_by_date(project, dates[0], dates[-1])
            full = [
                d.isoformat()
                for d in dates
                if capacity[d] is not None and len(taken.get(d, ())) >= capacity[d]
            ]
            if full:
                return _error("date_full", dates=full)

        absence = AbsenceRequest.objects.create(
            user=user,
            project=project,
            request_type=request_type,
            start_date=dates[0],
            end_date=dates[-1],
            days_count=len(dates),
            dates=[d.isoformat() for d in dates],
        )

        def _notify():
            from api.tasks import notify_coordinators_new_absence
            from core.tasks import send_absence_request_email

            send_absence_request_email.delay(absence.id)
            notify_coordinators_new_absence.delay(absence.id)

        transaction.on_commit(_notify)

    return JsonResponse({"request": _absence_payload(absence)}, status=201)


# --- Лікарняний: прикріплення документів -----------------------------------


@csrf_exempt
@require_POST
@telegram_auth()
def upload_sick_leave_documents(request, request_id: int):
    absence = (
        AbsenceRequest.objects.select_related("project", "project__region")
        .filter(id=request_id, user=request.app_user, request_type=RequestType.L4)
        .first()
    )
    if absence is None:
        return _error("not_found", 404)

    files = request.FILES.getlist("files")
    if not files:
        return _error("no_files")
    if len(files) > sick_leave_files.MAX_FILES_PER_UPLOAD:
        return _error("too_many_files", limit=sick_leave_files.MAX_FILES_PER_UPLOAD)
    if absence.documents.count() + len(files) > sick_leave_files.MAX_FILES_PER_REQUEST:
        return _error("too_many_files", limit=sick_leave_files.MAX_FILES_PER_REQUEST)
    if sum(f.size for f in files) > sick_leave_files.MAX_UPLOAD_BYTES:
        return _error(
            "upload_too_large",
            limit_mb=sick_leave_files.MAX_UPLOAD_BYTES // (1024 * 1024),
        )

    prepared = []
    for index, upload in enumerate(files, start=1):
        if upload.size > sick_leave_files.MAX_FILE_BYTES:
            return _error(
                "file_too_large",
                name=upload.name,
                limit_mb=sick_leave_files.MAX_FILE_BYTES // (1024 * 1024),
            )
        content = upload.read()
        detected = sick_leave_files.detect_file_type(content[:32])
        if detected is None:
            return _error("file_type", name=upload.name)
        content_type, extension = detected
        prepared.append(
            SickLeaveDocument(
                request=absence,
                filename=sick_leave_files.safe_filename(upload.name, extension, index),
                content_type=content_type,
                size=len(content),
                content=content,
            )
        )

    with transaction.atomic():
        created = SickLeaveDocument.objects.bulk_create(prepared)
        document_ids = [doc.id for doc in created]

        def _notify():
            from core.tasks import send_sick_leave_email

            send_sick_leave_email.delay(absence.id, document_ids)

        transaction.on_commit(_notify)

    absence = (
        AbsenceRequest.objects.select_related("project", "project__region")
        .prefetch_related("documents")
        .get(id=absence.id)
    )
    return JsonResponse({"request": _absence_payload(absence)}, status=201)


# --- Зголошення до адміністрації / бухгалтерії -----------------------------


@csrf_exempt
@require_POST
@telegram_auth()
def create_service_request(request):
    payload = _body(request)
    request_type = payload.get("type")
    text = (payload.get("text") or "").strip()

    if request_type not in RequestDepartment.values:
        return _error("bad_type")
    if not text:
        return _error("empty_text")
    if len(text) > MAX_SERVICE_TEXT:
        return _error("text_too_long", limit=MAX_SERVICE_TEXT)

    service_request = ServiceRequest.objects.create(
        user=request.app_user, request_type=request_type, text=text
    )

    def _notify():
        from core.tasks import send_service_request_email

        send_service_request_email.delay(service_request.id)

    transaction.on_commit(_notify)
    return JsonResponse({"request": _service_payload(service_request)}, status=201)


@require_GET
@telegram_auth()
def my_requests(request):
    user = request.app_user
    absence = [
        _absence_payload(r)
        for r in AbsenceRequest.objects.select_related("project", "project__region")
        .prefetch_related("documents")
        .filter(user=user)
        .order_by("-created_at")[:50]
    ]
    service = [
        _service_payload(r)
        for r in ServiceRequest.objects.filter(user=user).order_by("-created_at")[:50]
    ]
    items = sorted(
        absence + service, key=lambda item: item["created_at"], reverse=True
    )[:50]
    return JsonResponse({"requests": items})


# --- Панель координатора ----------------------------------------------------


def _coordinator_scope(user: User):
    qs = AbsenceRequest.objects.select_related(
        "user", "project", "project__region"
    ).prefetch_related("documents")
    if user.is_superuser:
        return qs
    return qs.filter(project__coordinators=user)


@require_GET
@telegram_auth(require_staff=True)
def coordinator_requests(request):
    status_filter = request.GET.get("filter", "new")
    qs = _coordinator_scope(request.app_user)
    if status_filter == "new":
        qs = qs.filter(status=RequestStatus.PENDING)
    elif status_filter == "processed":
        qs = qs.filter(~Q(status=RequestStatus.PENDING))
    items = [
        _absence_payload(r, with_worker=True) for r in qs.order_by("-created_at")[:100]
    ]
    return JsonResponse({"requests": items})


@csrf_exempt
@require_POST
@telegram_auth(require_staff=True)
def coordinator_decide(request, request_id: int):
    decision = _body(request).get("status")
    if decision not in (RequestStatus.APPROVED, RequestStatus.REJECTED):
        return _error("bad_status")

    with transaction.atomic():
        absence = (
            _coordinator_scope(request.app_user)
            .select_for_update(of=("self",))
            .filter(id=request_id)
            .first()
        )
        if absence is None:
            return _error("not_found", 404)
        if absence.status != RequestStatus.PENDING:
            return _error("already_decided", 409, status=absence.status)
        if decision == RequestStatus.REJECTED and not absence.can_be_rejected():
            return _error("l4_cannot_reject")

        absence.status = decision
        absence.decided_at = timezone.now()
        absence.decided_by = request.app_user
        absence.save(update_fields=["status", "decided_at", "decided_by"])

        def _notify():
            from api.tasks import notify_absence_decision

            notify_absence_decision.delay(absence.id)

        transaction.on_commit(_notify)

    return JsonResponse({"request": _absence_payload(absence, with_worker=True)})
