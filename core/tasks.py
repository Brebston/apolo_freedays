import requests

import time

from celery import shared_task

from django.utils import timezone
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

_STATUS_LABELS_PL = {
    "pending": ("Oczekuje", "#fef6e7", "#b7791f"),
    "approved": ("Zatwierdzono", "#e8f6ee", "#1e7e45"),
    "rejected": ("Odrzucono", "#fdecec", "#c0392b"),
}
_TYPE_LABELS_PL = {
    "dayoff": "Dzień wolny",
    "l4": "Zwolnienie lekarskie (L4)",
}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_absence_request_email(self, request_id: int):
    from core.models import AbsenceRequest, EmailRecipientType

    try:
        req = AbsenceRequest.objects.select_related(
            "user", "project", "project__region"
        ).get(id=request_id)
    except AbsenceRequest.DoesNotExist:
        return

    recipients = list(req.project.email_recipients.all())
    to_list = [r.email for r in recipients if r.recipient_type == EmailRecipientType.TO]
    cc_list = [r.email for r in recipients if r.recipient_type == EmailRecipientType.CC]

    if not to_list:
        return

    status_label, status_bg, status_color = _STATUS_LABELS_PL.get(
        req.status,
        (req.status, "#f2f4f7", "#344054"),
    )
    type_label = _TYPE_LABELS_PL.get(req.request_type, req.request_type)

    context = {
        "worker_name": f"{req.user.last_name} {req.user.first_name}",
        "worker_email": req.user.email,
        "worker_phone": req.user.phone,
        "project_name": req.project.name,
        "region_name": req.project.region.name,
        "type_label": type_label,
        "start_date": req.start_date,
        "end_date": req.end_date,
        "days_count": req.days_count,
        "status_label": status_label,
        "status_bg": status_bg,
        "status_color": status_color,
    }
    html_body = render_to_string("core/emails/new_absence_request.html", context)

    subject = f"Nowe zgłoszenie: {type_label} — {req.project.name}"
    text_body = (
        f"Pracownik: {req.user.last_name} {req.user.first_name}\n"
        f"Email: {req.user.email}\n"
        f"Telefon: {req.user.phone}\n"
        f"Projekt: {req.project.name} ({req.project.region.name})\n"
        f"Rodzaj: {type_label}\n"
        f"Termin: {req.start_date} — {req.end_date}\n"
        f"Liczba dni: {req.days_count}\n"
        f"Status: {status_label}\n"
    )

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to_list,
            cc=cc_list or None,
        )
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_worker_telegram(self, request_id: int):
    from core.models import AbsenceRequest, RequestStatus
    from bot.locales import t

    try:
        req = AbsenceRequest.objects.select_related("user", "project").get(
            id=request_id
        )
    except AbsenceRequest.DoesNotExist:
        return

    if req.status == RequestStatus.PENDING or not req.user.telegram_id:
        return

    text = t(
        "request_decided_worker",
        req.user.language,
        status=t(f"status_{req.status}", req.user.language),
        start=req.start_date,
        end=req.end_date,
        project=req.project.name,
    )
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url, json={"chat_id": req.user.telegram_id, "text": text}, timeout=10
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_broadcast_message(self, broadcast_id: int):
    """
    Sends a single newsletter to all its recipients via the Telegram Bot API
    (directly via HTTP, without Aiogram—the Celery task is synchronous).
    """
    from core.models import Broadcast

    try:
        broadcast = Broadcast.objects.get(id=broadcast_id)
    except Broadcast.DoesNotExist:
        return

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    sent_count = 0
    failed_count = 0

    for user in broadcast.get_recipients():
        payload = {
            "chat_id": user.telegram_id,
            "text": broadcast.text,
            "parse_mode": "HTML",
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 429:
                retry_after = resp.json().get("parameters", {}).get("retry_after", 1)
                time.sleep(retry_after)
                resp = requests.post(url, json=payload, timeout=10)
            if resp.ok:
                sent_count += 1
            else:
                failed_count += 1
        except requests.RequestException:
            failed_count += 1
        time.sleep(0.05)  # Precautions Against Telegram's Rate Limit

    broadcast.last_sent_at = timezone.now()
    broadcast.last_sent_count = sent_count
    broadcast.last_failed_count = failed_count
    broadcast.save(
        update_fields=["last_sent_at", "last_sent_count", "last_failed_count"]
    )


@shared_task
def check_and_send_due_broadcasts():
    """
    Periodic task (Celery Beat, every 5 minutes): checks all active
    mailings and queues those that are due to be sent—
    both one-time mailings based on `scheduled_at` and recurring mailings based on `recurrence`.
    """
    from core.models import Broadcast

    now = timezone.now()
    for broadcast in Broadcast.objects.filter(is_active=True):
        if broadcast.is_due(now):
            send_broadcast_message.delay(broadcast.id)
