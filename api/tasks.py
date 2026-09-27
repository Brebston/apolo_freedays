"""
Telegram-сповіщення, які ініціює Mini App (надсилаються з Celery через Bot API).

Формат callback_data кнопок ("decide:<id>:approved") збігається з тим, що
обробляє bot/handlers/coordinator.py — тож координатор може ухвалити рішення
як прямо в чаті бота, так і в застосунку.
"""

import requests
from celery import shared_task
from django.conf import settings


def _send_message(
    chat_id: int, text: str, reply_markup: dict | None = None
) -> dict | None:
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    response = requests.post(
        f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage",
        json=payload,
        timeout=10,
    )
    if response.ok:
        return response.json().get("result")
    return None


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_coordinators_new_absence(self, request_id: int):
    from bot.locales import t
    from core.models import AbsenceRequest

    try:
        req = AbsenceRequest.objects.select_related(
            "user", "project", "project__region"
        ).get(id=request_id)
    except AbsenceRequest.DoesNotExist:
        return

    coordinators = req.project.coordinators.filter(
        is_staff=True, is_active=True, telegram_id__isnull=False
    )
    message_ids = dict(req.notified_coordinator_message_ids or {})

    for coordinator in coordinators:
        lang = coordinator.language
        type_label = (
            t("btn_l4", lang) if req.request_type == "l4" else t("btn_dayoff", lang)
        )
        text = t(
            "coordinator_new_request_notification",
            lang,
            name=f"{req.user.last_name} {req.user.first_name}",
            link=f"tg://user?id={req.user.telegram_id}",
            project=req.project.name,
            region=req.project.region.name,
            type=type_label,
            start=req.start_date,
            end=req.end_date,
        )
        buttons = [
            {
                "text": t("btn_approve", lang),
                "callback_data": f"decide:{req.id}:approved",
            }
        ]
        if req.can_be_rejected():
            buttons.append(
                {
                    "text": t("btn_reject", lang),
                    "callback_data": f"decide:{req.id}:rejected",
                }
            )

        try:
            sent = _send_message(
                coordinator.telegram_id, text, {"inline_keyboard": [buttons]}
            )
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
        req = AbsenceRequest.objects.select_related("user", "project").get(
            id=request_id
        )
    except AbsenceRequest.DoesNotExist:
        return
    if not req.user.telegram_id:
        return

    lang = req.user.language
    text = t(
        "request_decided_worker",
        lang,
        status=t(f"status_{req.status}", lang),
        start=req.start_date,
        end=req.end_date,
        project=req.project.name,
    )
    try:
        _send_message(req.user.telegram_id, text)
    except requests.RequestException as exc:
        raise self.retry(exc=exc)


def _telegram(method: str, payload: dict) -> dict | None:
    response = requests.post(
        f"https://api.telegram.org/bot{settings.BOT_TOKEN}/{method}",
        json=payload,
        timeout=10,
    )
    return response.json().get("result") if response.ok else None


def _open_app_markup(lang: str) -> dict | None:
    from bot.locales import t

    if not settings.WEBAPP_URL:
        return None
    return {
        "inline_keyboard": [
            [{"text": t("btn_open_app", lang), "web_app": {"url": settings.WEBAPP_URL}}]
        ]
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_absence_cancelled(self, request_id: int):
    """
    Працівник скасував заявку: прибираємо кнопки рішення з push-повідомлень
    координаторів (щоб не можна було вирішити скасовану заявку), відповідаємо
    на них поясненням і надсилаємо лист адресатам проєкту.
    """
    from bot.locales import t
    from core.models import AbsenceRequest
    from core.tasks import send_absence_request_email
    from users.models import User

    try:
        req = AbsenceRequest.objects.select_related("user", "project").get(
            id=request_id
        )
    except AbsenceRequest.DoesNotExist:
        return

    worker = f"{req.user.last_name} {req.user.first_name}"
    for chat_id, message_id in (req.notified_coordinator_message_ids or {}).items():
        coordinator = User.objects.filter(telegram_id=int(chat_id)).first()
        lang = coordinator.language if coordinator else "uk"
        try:
            _telegram(
                "editMessageReplyMarkup",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )
            _telegram(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": t(
                        "request_cancelled_coordinator",
                        lang,
                        name=worker,
                        start=req.start_date,
                        end=req.end_date,
                        project=req.project.name,
                    ),
                    "reply_parameters": {
                        "message_id": message_id,
                        "allow_sending_without_reply": True,
                    },
                },
            )
        except requests.RequestException as exc:
            raise self.retry(exc=exc)

    send_absence_request_email.delay(req.id, "cancelled")


@shared_task
def notify_service_request_cancelled(service_request_id: int):
    """Лист відповідальним особам відділу: посилання «Прийняти/Відхилити» більше не діють."""
    from django.core.mail import send_mail

    from core.models import DepartmentResponsiblePerson, ServiceRequest

    sr = (
        ServiceRequest.objects.select_related("user")
        .filter(id=service_request_id)
        .first()
    )
    if sr is None:
        return
    emails = sorted(
        {
            person.user.email
            for person in DepartmentResponsiblePerson.objects.filter(
                department=sr.request_type
            ).select_related("user")
            if person.user.email
        }
    )
    if not emails:
        return
    worker = f"{sr.user.last_name} {sr.user.first_name}"
    send_mail(
        subject=f"Anulowano zgłoszenie — {worker}",
        message=(
            f"Pracownik {worker} anulował zgłoszenie.\n\n"
            f"Treść: {sr.text}\n\n"
            "Przyciski decyzji w poprzedniej wiadomości nie są już aktywne."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=emails,
    )


@shared_task
def remind_missing_sick_notes():
    """
    Щодня: нагадує працівникам прикріпити лікарняний, якщо L4 подано
    SICK_NOTE_REMINDER_AFTER_DAYS днів тому, а документа досі немає.
    Не більше SICK_NOTE_REMINDER_MAX нагадувань з інтервалом SICK_NOTE_REMINDER_INTERVAL_DAYS.
    """
    from datetime import timedelta

    from django.db.models import Q
    from django.utils import timezone

    from bot.locales import t
    from core.models import INACTIVE_STATUSES, AbsenceRequest, RequestType

    now = timezone.now()
    due = (
        AbsenceRequest.objects.select_related("user", "project")
        .filter(
            request_type=RequestType.L4,
            documents__isnull=True,
            created_at__lte=now
            - timedelta(days=settings.SICK_NOTE_REMINDER_AFTER_DAYS),
            sick_note_reminders_sent__lt=settings.SICK_NOTE_REMINDER_MAX,
            user__is_active=True,
            user__telegram_id__isnull=False,
        )
        .filter(
            Q(sick_note_last_reminded_at__isnull=True)
            | Q(
                sick_note_last_reminded_at__lte=now
                - timedelta(days=settings.SICK_NOTE_REMINDER_INTERVAL_DAYS)
            )
        )
        .exclude(status__in=INACTIVE_STATUSES)
        .distinct()
    )

    sent = 0
    for req in due:
        lang = req.user.language
        text = t(
            "l4_missing_document_reminder",
            lang,
            start=req.start_date.strftime("%d.%m"),
            end=req.end_date.strftime("%d.%m"),
            project=req.project.name,
        )
        payload = {"chat_id": req.user.telegram_id, "text": text}
        markup = _open_app_markup(lang)
        if markup:
            payload["reply_markup"] = markup
        try:
            delivered = _telegram("sendMessage", payload) is not None
        except requests.RequestException:
            continue  # спробуємо наступного дня; лічильник не збільшуємо
        if delivered:
            AbsenceRequest.objects.filter(id=req.id).update(
                sick_note_reminders_sent=req.sick_note_reminders_sent + 1,
                sick_note_last_reminded_at=now,
            )
            sent += 1
    return sent
