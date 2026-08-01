from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
import requests


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_absence_request_email(self, request_id: int):
    """
    Формує та надсилає email про нове зголошення отримувачам проєкту
    (To / DW-CC), налаштованим у Django Admin (п.4.5 ТЗ).
    """
    from core.models import AbsenceRequest, EmailRecipientType

    try:
        req = (
            AbsenceRequest.objects
            .select_related("user", "project", "project__region")
            .get(id=request_id)
        )
    except AbsenceRequest.DoesNotExist:
        return

    recipients = list(req.project.email_recipients.all())
    to_list = [r.email for r in recipients if r.recipient_type == EmailRecipientType.TO]
    cc_list = [r.email for r in recipients if r.recipient_type == EmailRecipientType.CC]

    if not to_list:
        # Немає жодного налаштованого прямого отримувача — нема кому надсилати.
        return

    subject = f"Нове зголошення: {req.get_request_type_display()} — {req.project.name}"
    body = (
        f"Працівник: {req.user.last_name} {req.user.first_name}\n"
        f"Email: {req.user.email}\n"
        f"Телефон: {req.user.phone}\n"
        f"Проєкт: {req.project.name} ({req.project.region.name})\n"
        f"Тип: {req.get_request_type_display()}\n"
        f"Дати: {req.start_date} — {req.end_date}\n"
        f"Кількість днів: {req.days_count}\n"
        f"Статус: {req.get_status_display()}\n"
    )

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to_list,
            cc=cc_list or None,
        )
        email.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_worker_telegram(self, request_id: int):
    from core.models import AbsenceRequest, RequestStatus
    from bot.locales import t

    try:
        req = AbsenceRequest.objects.select_related("user", "project").get(id=request_id)
    except AbsenceRequest.DoesNotExist:
        return

    if req.status == RequestStatus.PENDING or not req.user.telegram_id:
        return

    text = t(
        "request_decided_worker", req.user.language,
        status=t(f"status_{req.status}", req.user.language),
        start=req.start_date, end=req.end_date,
        project=req.project.name,
    )
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": req.user.telegram_id, "text": text}, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise self.retry(exc=exc)