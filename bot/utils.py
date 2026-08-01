from datetime import date

from asgiref.sync import sync_to_async
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from django.utils import timezone

from core.models import AbsenceRequest, Project, Region, RequestStatus
from users.models import User, latin_name_validator


def is_valid_name(value: str) -> bool:
    try:
        latin_name_validator(value)
        return bool(value)
    except ValidationError:
        return False


def is_valid_email(value: str) -> bool:
    try:
        django_validate_email(value)
        return True
    except ValidationError:
        return False


# ---------------------------------------------------------------------------
# Users / auth
# ---------------------------------------------------------------------------

@sync_to_async
def get_user_by_telegram_id(telegram_id: int):
    return User.objects.filter(telegram_id=telegram_id).first()


@sync_to_async
def get_user_by_email(email: str):
    return User.objects.filter(email__iexact=email).first()


@sync_to_async
def create_user(telegram_id, first_name, last_name, email, phone, password, language):
    user = User(
        telegram_id=telegram_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        language=language,
    )
    user.password = make_password(password)
    user.save()
    return user


@sync_to_async
def link_telegram_and_check_password(email: str, password: str, telegram_id: int):
    user = User.objects.filter(email__iexact=email).first()
    if not user or not check_password(password, user.password):
        return None
    user.telegram_id = telegram_id
    user.save(update_fields=["telegram_id"])
    return user


@sync_to_async
def set_user_language(telegram_id: int, language: str):
    User.objects.filter(telegram_id=telegram_id).update(language=language)


# ---------------------------------------------------------------------------
# Regions / projects
# ---------------------------------------------------------------------------

@sync_to_async
def get_regions():
    return list(Region.objects.all().order_by("name"))


@sync_to_async
def get_projects_by_region(region_id: int):
    return list(Project.objects.filter(region_id=region_id).order_by("name"))


@sync_to_async
def get_project(project_id: int):
    return Project.objects.select_related("region").filter(id=project_id).first()


@sync_to_async
def get_project_coordinators(project_id: int):
    project = Project.objects.prefetch_related("coordinators").get(id=project_id)
    return list(project.coordinators.filter(is_staff=True, telegram_id__isnull=False))


@sync_to_async
def get_coordinators_by_region(region_id: int):
    return list(
        User.objects.filter(
            is_staff=True, coordinated_projects__region_id=region_id,
        ).distinct()
    )


@sync_to_async
def get_coordinator_project_ids(user_id: int):
    return list(Project.objects.filter(coordinators__id=user_id).values_list("id", flat=True))


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

@sync_to_async
def create_absence_request(user_id: int, project_id: int, request_type: str, dates: list[str]):
    dates_sorted = sorted(dates)
    start = date.fromisoformat(dates_sorted[0])
    end = date.fromisoformat(dates_sorted[-1])
    return AbsenceRequest.objects.create(
        user_id=user_id,
        project_id=project_id,
        request_type=request_type,
        start_date=start,
        end_date=end,
        days_count=len(dates_sorted),
    )


@sync_to_async
def get_request(request_id: int):
    return (
        AbsenceRequest.objects
        .select_related("user", "project", "project__region")
        .filter(id=request_id)
        .first()
    )


@sync_to_async
def decide_request(request_id: int, status: str, decided_by_id: int):
    req = (
        AbsenceRequest.objects
        .select_related("user", "project")
        .get(id=request_id)
    )
    if req.status != RequestStatus.PENDING:
        return req, False
    req.status = status
    req.decided_at = timezone.now()
    req.decided_by_id = decided_by_id
    req.save(update_fields=["status", "decided_at", "decided_by_id"])
    return req, True


@sync_to_async
def get_my_requests(user_id: int):
    return list(
        AbsenceRequest.objects.select_related("project").filter(user_id=user_id).order_by("-created_at")[:20]
    )


@sync_to_async
def get_project_requests(project_ids: list[int], status_filter: str | None):
    qs = AbsenceRequest.objects.filter(project_id__in=project_ids).select_related("user", "project")
    if status_filter == "new":
        qs = qs.filter(status=RequestStatus.PENDING)
    elif status_filter == "processed":
        qs = qs.exclude(status=RequestStatus.PENDING)
    return list(qs.order_by("-created_at")[:30])


@sync_to_async
def save_notification_message_id(request_id: int, coordinator_telegram_id: int, message_id: int):
    req = AbsenceRequest.objects.get(id=request_id)
    data = req.notified_coordinator_message_ids or {}
    data[str(coordinator_telegram_id)] = message_id
    req.notified_coordinator_message_ids = data
    req.save(update_fields=["notified_coordinator_message_ids"])
