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
    "cancelled": ("Anulowano przez pracownika", "#f2f4f7", "#475467"),
}
_TYPE_LABELS_PL = {
    "dayoff": "Dzień wolny",
    "l4": "Zwolnienie lekarskie (L4)",
}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_absence_request_email(self, request_id: int, event: str = "new"):
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
        "heading": (
            "❌ Zgłoszenie anulowane"
            if event == "cancelled"
            else "📋 Nowe zgłoszenie nieobecności"
        ),
    }
    html_body = render_to_string("core/emails/new_absence_request.html", context)

    prefix = "Anulowano" if event == "cancelled" else "Nowe zgłoszenie"
    subject = f"{prefix}: {type_label} — {req.project.name}"
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


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_service_request_email(self, service_request_id: int):
    """
    Sends an email notification about a new submission to the
    administration/accounting department, featuring clickable
    "Accept" and "Reject" buttons directly in the message—the
    links point to a public Django view secured by a unique
    `decision_token` (no login required).
    """
    from core.models import (
        DepartmentResponsiblePerson,
        EmailRecipientType,
        ServiceRequest,
    )

    try:
        sr = ServiceRequest.objects.select_related("user").get(id=service_request_id)
    except ServiceRequest.DoesNotExist:
        return

    recipients = DepartmentResponsiblePerson.objects.filter(
        department=sr.request_type
    ).select_related("user")
    to_list = [
        r.user.email
        for r in recipients
        if r.recipient_type == EmailRecipientType.TO and r.user.email
    ]
    cc_list = [
        r.user.email
        for r in recipients
        if r.recipient_type == EmailRecipientType.CC and r.user.email
    ]

    if not to_list:
        return

    base_url = settings.SITE_BASE_URL.rstrip("/")
    approve_url = f"{base_url}/requests/{sr.decision_token}/approve/"
    reject_url = f"{base_url}/requests/{sr.decision_token}/reject/"

    type_label_pl = (
        "Zgłoszenie do administracji"
        if sr.request_type == "administration"
        else "Zgłoszenie do księgowości"
    )

    context = {
        "worker_name": f"{sr.user.last_name} {sr.user.first_name}",
        "worker_email": sr.user.email,
        "worker_phone": sr.user.phone,
        "type_label": type_label_pl,
        "text": sr.text,
        "approve_url": approve_url,
        "reject_url": reject_url,
    }
    html_body = render_to_string("core/emails/new_service_request.html", context)

    subject = f"Nowe zgłoszenie: {type_label_pl}"
    text_body = (
        f"Pracownik: {sr.user.last_name} {sr.user.first_name}\n"
        f"Email: {sr.user.email}\n"
        f"Rodzaj: {type_label_pl}\n"
        f"Treść: {sr.text}\n\n"
        f"Zaakceptuj: {approve_url}\n"
        f"Odrzuć: {reject_url}\n"
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
def notify_service_request_decision(self, service_request_id: int):
    """Push notification to the employee via Telegram following a decision on the submission (via email)."""
    import requests

    from bot.locales import t
    from core.models import ServiceRequest

    try:
        sr = ServiceRequest.objects.select_related("user").get(id=service_request_id)
    except ServiceRequest.DoesNotExist:
        return

    if not sr.user.telegram_id:
        return

    lang = sr.user.language
    type_label = (
        t("btn_administration", lang)
        if sr.request_type == "administration"
        else t("btn_accounting", lang)
    )
    status_label = t(f"status_{sr.status}", lang)
    text = t(
        "service_request_decided_worker",
        lang,
        status=status_label,
        type=type_label,
        text=sr.text,
    )

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url, json={"chat_id": sr.user.telegram_id, "text": text}, timeout=10
        )
    except requests.RequestException as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_sick_leave_email(self, request_id: int, document_ids: list[int]):
    """
    Лист з файлами лікарняного тим самим адресатам To/CC проєкту, що отримують
    лист про саму заявку. Стиль і поля — як у new_absence_request.html.
    """
    from core.models import AbsenceRequest, EmailRecipientType, SickLeaveDocument
    from core.services import request_dates

    try:
        req = AbsenceRequest.objects.select_related(
            "user", "project", "project__region"
        ).get(id=request_id)
    except AbsenceRequest.DoesNotExist:
        return

    documents = list(
        SickLeaveDocument.objects.filter(
            request=req, id__in=document_ids, content__isnull=False
        )
    )
    if not documents:
        return

    recipients = list(req.project.email_recipients.all())
    to_list = [r.email for r in recipients if r.recipient_type == EmailRecipientType.TO]
    cc_list = [r.email for r in recipients if r.recipient_type == EmailRecipientType.CC]
    if not to_list:
        return

    is_supplement = (
        req.documents.filter(emailed_at__isnull=False)
        .exclude(id__in=document_ids)
        .exists()
    )
    absence_dates = request_dates(req)
    worker_name = f"{req.user.last_name} {req.user.first_name}"

    context = {
        "worker_name": worker_name,
        "worker_email": req.user.email,
        "worker_phone": req.user.phone,
        "project_name": req.project.name,
        "region_name": req.project.region.name,
        "start_date": req.start_date,
        "end_date": req.end_date,
        "absence_dates": absence_dates,
        "days_count": req.days_count,
        "attachments": documents,
        "is_supplement": is_supplement,
    }
    html_body = render_to_string("core/emails/sick_leave_document.html", context)

    prefix = (
        "Uzupełnienie: zwolnienie lekarskie"
        if is_supplement
        else "Zwolnienie lekarskie (L4)"
    )
    subject = f"{prefix} — {worker_name} — {req.project.name}"
    text_body = (
        f"Pracownik: {worker_name}\n"
        f"Email: {req.user.email or '—'}\n"
        f"Telefon: {req.user.phone or '—'}\n"
        f"Projekt: {req.project.name} ({req.project.region.name})\n"
        f"Termin: {req.start_date:%d.%m.%Y} — {req.end_date:%d.%m.%Y}\n"
        f"Dni nieobecności: {', '.join(d.strftime('%d.%m.%Y') for d in absence_dates)}\n"
        f"Liczba dni: {req.days_count}\n"
        f"Załączniki: {', '.join(doc.filename for doc in documents)}\n"
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
        for doc in documents:
            email.attach(doc.filename, bytes(doc.content), doc.content_type)
        email.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)

    SickLeaveDocument.objects.filter(id__in=[doc.id for doc in documents]).update(
        emailed_at=timezone.now()
    )


@shared_task
def purge_old_sick_leave_files():
    """
    Щодня: видаляє вміст файлів, які вже надіслані координатору понад
    SICK_LEAVE_FILE_RETENTION_DAYS днів тому. Запис (назва, розмір, дати) лишається,
    копія файлу — у листі координатора. Ручне чищення бази не потрібне.
    """
    from datetime import timedelta

    from core.models import SickLeaveDocument

    cutoff = timezone.now() - timedelta(days=settings.SICK_LEAVE_FILE_RETENTION_DAYS)
    return SickLeaveDocument.objects.filter(
        emailed_at__lt=cutoff,
        content__isnull=False,
    ).update(content=None, purged_at=timezone.now())
