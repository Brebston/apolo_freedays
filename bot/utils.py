from datetime import date

from asgiref.sync import sync_to_async
from django.utils import timezone

from core.models import AbsenceRequest, Project, Region, RequestStatus, RequestType
from users.models import User

# ---------------------------------------------------------------------------
# Users / auth
# ---------------------------------------------------------------------------


@sync_to_async
def get_user_by_telegram_id(telegram_id: int):
    return User.objects.filter(telegram_id=telegram_id).first()


@sync_to_async
def get_active_user_by_telegram_id(telegram_id: int):
    """
    Same as get_user_by_telegram_id, but returns the user only if is_active=True.
    It is used in all handlers that provide access to the bot's functionality—unlike
    get_user_by_telegram_id, which remains a "raw" lookup for cases where we handle
    an inactive user ourselves (e.g., /start).
    """
    return User.objects.filter(telegram_id=telegram_id, is_active=True).first()


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
            is_staff=True,
            coordinated_projects__region_id=region_id,
        ).distinct()
    )


@sync_to_async
def get_coordinator_project_ids(user_id: int):
    return list(
        Project.objects.filter(coordinators__id=user_id).values_list("id", flat=True)
    )


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


@sync_to_async
def create_absence_request(
    user_id: int, project_id: int, request_type: str, dates: list[str]
):
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
        dates=dates_sorted,
    )


@sync_to_async
def get_used_dayoff_days_in_month(
    user_id: int,
    project_id: int,
    year: int,
    month: int,
    exclude_request_id: int | None = None,
) -> int:
    """
    The total number of days off taken by the employee for the project in the specified
    calendar month—across all their "Day Off" requests, excluding rejected ones.
    """
    qs = AbsenceRequest.objects.filter(
        user_id=user_id, project_id=project_id, request_type=RequestType.DAYOFF
    ).exclude(status=RequestStatus.REJECTED)
    if exclude_request_id:
        qs = qs.exclude(id=exclude_request_id)

    prefix = f"{year:04d}-{month:02d}"
    total = 0
    for req in qs.only("dates", "start_date", "end_date", "days_count"):
        dates = req.dates or []
        if dates:
            total += sum(1 for iso in dates if iso.startswith(prefix))
        elif (
            req.start_date.year == year
            and req.start_date.month == month
            and req.end_date.year == year
            and req.end_date.month == month
        ):
            total += req.days_count
    return total


@sync_to_async
def get_workers_count_on_date(project_id: int, iso_date: str) -> int:
    """
    The number of UNIQUE project workers who already have a scheduled day off
    (that has not been rejected) on a specific date. Used for the `Project.max_workers_per_day` limit.
    """
    qs = AbsenceRequest.objects.filter(
        project_id=project_id, request_type=RequestType.DAYOFF
    ).exclude(status=RequestStatus.REJECTED)
    user_ids = set()
    for req in qs.only("dates", "start_date", "end_date", "user_id"):
        dates = req.dates or []
        if dates:
            if iso_date in dates:
                user_ids.add(req.user_id)
        elif req.start_date.isoformat() <= iso_date <= req.end_date.isoformat():
            user_ids.add(req.user_id)
    return len(user_ids)


@sync_to_async
def get_date_capacity_limit(project_id: int, iso_date: str) -> int | None:
    """
    Returns the worker limit if an override (ProjectDateLimit) is configured for this specific date in
    the Django Admin. If no override exists, it returns None, in which case the general
    Project.max_workers_per_day should be used.
    """
    from core.models import ProjectDateLimit

    entry = ProjectDateLimit.objects.filter(
        project_id=project_id, date=iso_date
    ).first()
    return entry.max_workers if entry else None


@sync_to_async
def get_request(request_id: int):
    return (
        AbsenceRequest.objects.select_related("user", "project", "project__region")
        .filter(id=request_id)
        .first()
    )


@sync_to_async
def decide_request(request_id: int, status: str, decided_by_id: int):
    req = AbsenceRequest.objects.select_related("user", "project").get(id=request_id)
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
        AbsenceRequest.objects.select_related("project")
        .filter(user_id=user_id)
        .order_by("-created_at")[:20]
    )


@sync_to_async
def get_project_requests(project_ids: list[int], status_filter: str | None):
    qs = AbsenceRequest.objects.filter(project_id__in=project_ids).select_related(
        "user", "project"
    )
    if status_filter == "new":
        qs = qs.filter(status=RequestStatus.PENDING)
    elif status_filter == "processed":
        qs = qs.exclude(status=RequestStatus.PENDING)
    return list(qs.order_by("-created_at")[:30])


@sync_to_async
def save_notification_message_id(
    request_id: int, coordinator_telegram_id: int, message_id: int
):
    req = AbsenceRequest.objects.get(id=request_id)
    data = req.notified_coordinator_message_ids or {}
    data[str(coordinator_telegram_id)] = message_id
    req.notified_coordinator_message_ids = data
    req.save(update_fields=["notified_coordinator_message_ids"])
