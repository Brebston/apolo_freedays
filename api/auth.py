"""Декоратор авторизації Mini App API за підписаним Telegram initData."""

import functools

from django.conf import settings
from django.http import JsonResponse

from api.telegram_init_data import InitDataError, validate_init_data
from users.models import User

INIT_DATA_HEADER = "HTTP_X_TELEGRAM_INIT_DATA"


def _resolve_telegram_user(request) -> dict | None:
    init_data = request.META.get(INIT_DATA_HEADER, "")
    if init_data:
        try:
            return validate_init_data(init_data, settings.BOT_TOKEN)["user"]
        except InitDataError:
            return None

    # Лише для локальної розробки в браузері (поза Telegram): DEBUG=1 і явно
    # заданий WEBAPP_DEV_TELEGRAM_ID. У продакшн (DEBUG=0) ця гілка не діє.
    dev_id = getattr(settings, "WEBAPP_DEV_TELEGRAM_ID", "")
    if settings.DEBUG and dev_id:
        return {"id": int(dev_id), "first_name": "Dev"}
    return None


def telegram_auth(require_access: bool = True, require_staff: bool = False):
    """
    request.tg_user  — дані користувача з Telegram (dict)
    request.app_user — User з is_active=True або None, якщо доступу немає
    """

    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            tg_user = _resolve_telegram_user(request)
            if tg_user is None:
                return JsonResponse({"error": "unauthorized"}, status=401)

            request.tg_user = tg_user
            request.app_user = User.objects.filter(
                telegram_id=tg_user["id"], is_active=True
            ).first()

            if require_access and request.app_user is None:
                return JsonResponse({"error": "no_access"}, status=403)
            if require_staff and not (request.app_user and request.app_user.is_staff):
                return JsonResponse({"error": "forbidden"}, status=403)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
