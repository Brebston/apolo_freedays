"""
Telegram-сповіщення, які ініціює Mini App (надсилаються з Celery через Bot API).

Формат callback_data кнопок ("decide:<id>:approved") збігається з тим, що
обробляє bot/handlers/coordinator.py — тож координатор може ухвалити рішення
як прямо в чаті бота, так і в застосунку.
"""

import requests
from celery import shared_task
from django.conf import settings


def _send_message(chat_id: int, text: str, reply_markup: dict | None = None) -> dict | None:
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    response = requests.post(
        f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage", json=payload, timeout=10,
    )
    if response.ok:
        return response.json().get("result")
    return None


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_coordinators_new_absence(self, request_id: int):
    from bot.locales import t
    from core.models import AbsenceRequest

    try:
        req = AbsenceRequest.objects.select_related("user", "project", "project__region").get(id=request_id)
    except AbsenceRequest.DoesNotExist:
        return

    coordinators = req.project.coordinators.filter(is_staff=True, is_active=True, telegram_id__isnull=False)
    message_ids = dict(req.notified_coordinator_message_ids or {})

    for coordinator in coordinators:
        lang = coordinator.language
        type_label = t("btn_l4", lang) if req.request_type == "l4" else t("btn_dayoff", lang)
        text = t(
            "coordinator_new_request_notification", lang,
            name=f"{req.user.last_name} {req.user.first_name}",
            link=f"tg://user?id={req.user.telegram_id}",
            project=req.project.name, region=req.project.region.name,
            type=type_label, start=req.start_date, end=req.end_date,
        )
        buttons = [{"text": t("btn_approve", lang), "callback_data": f"decide:{req.id}:approved"}]
        if req.can_be_rejected():
            buttons.append({"text": t("btn_reject", lang), "callback_data": f"decide:{req.id}:rejected"})

        try:
            sent = _send_message(coordinator.telegram_id, text, {"inline_keyboard": [buttons]})
        except requests.RequestException as exc:
            raise self.retry(exc=exc)
        if sent:
            message_ids[str(coordinator.telegram_id)] = sent["message_id"]

    req.notified_coordinator_message_ids = message_ids
    req.save(update_fields=["notified_coordinator_message_ids"])


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_absence_decision(self, request_id: int):
    from bot.locales import t
    from core.models import AbsenceRequest

    try:
        req = AbsenceRequest.objects.select_related("user", "project").get(id=request_id)
    except AbsenceRequest.DoesNotExist:
        return
    if not req.user.telegram_id:
        return

    lang = req.user.language
    text = t(
        "request_decided_worker", lang,
        status=t(f"status_{req.status}", lang),
        start=req.start_date, end=req.end_date, project=req.project.name,
    )
    try:
        _send_message(req.user.telegram_id, text)
    except requests.RequestException as exc:
        raise self.retry(exc=exc)
