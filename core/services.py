"""
Бізнес-логіка лімітів вихідних для Mini App API (синхронна версія).

Правила ті самі, що й у боті (bot/utils.py): місячний ліміт вихідних
на працівника в проєкті, ліміт працівників на дату з перевизначенням
через ProjectDateLimit. Відхилені зголошення не враховуються.
"""

import calendar
from collections import defaultdict
from datetime import date, timedelta

from core.models import AbsenceRequest, ProjectDateLimit, RequestStatus, RequestType, INACTIVE_STATUSES

L4_MAX_DAYS = 31


def request_dates(req) -> list[date]:
    """Точний список дат зголошення: з поля dates, а для старих записів — інтервал start..end."""
    if req.dates:
        return [date.fromisoformat(iso) for iso in req.dates]
    days = (req.end_date - req.start_date).days
    return [req.start_date + timedelta(days=i) for i in range(days + 1)]


def month_bounds(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def _active_requests(project_id: int, start: date, end: date, request_type: str | None = None):
    qs = (
        AbsenceRequest.objects
        .filter(project_id=project_id, start_date__lte=end, end_date__gte=start)
        .exclude(status__in=INACTIVE_STATUSES)
        .only("user_id", "request_type", "dates", "start_date", "end_date")
    )
    if request_type:
        qs = qs.filter(request_type=request_type)
    return qs


def occupancy(project_id: int, start: date, end: date) -> dict[date, set[int]]:
    """Для кожної дати діапазону — множина працівників, що вже мають вихідний (не відхилений)."""
    result: dict[date, set[int]] = defaultdict(set)
    for req in _active_requests(project_id, start, end, RequestType.DAYOFF):
        for d in request_dates(req):
            if start <= d <= end:
                result[d].add(req.user_id)
    return result


def user_dates(user_id: int, project_id: int, start: date, end: date) -> dict[date, str]:
    """Дати, які працівник уже подав у цьому проєкті (будь-який тип, не відхилені) -> тип."""
    result: dict[date, str] = {}
    for req in _active_requests(project_id, start, end).filter(user_id=user_id):
        for d in request_dates(req):
            if start <= d <= end:
                result[d] = req.request_type
    return result


def used_dayoff_in_month(user_id: int, project_id: int, year: int, month: int) -> int:
    start, end = month_bounds(year, month)
    return sum(1 for kind in user_dates(user_id, project_id, start, end).values() if kind == RequestType.DAYOFF)


def capacity_by_date(project, start: date, end: date) -> dict[date, int | None]:
    """Ефективний ліміт працівників на кожну дату: перевизначення або загальний ліміт проєкту."""
    overrides = {
        item.date: item.max_workers
        for item in ProjectDateLimit.objects.filter(project=project, date__gte=start, date__lte=end)
    }
    result = {}
    d = start
    while d <= end:
        result[d] = overrides.get(d, project.max_workers_per_day)
        d += timedelta(days=1)
    return result
