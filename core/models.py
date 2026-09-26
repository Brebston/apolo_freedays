import calendar as cal_module

import secrets

from django.core.validators import MaxValueValidator, MinValueValidator
from django.conf import settings
from django.db import models


class Region(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Region name")

    class Meta:
        verbose_name = "Region"
        verbose_name_plural = "Regions"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=150, verbose_name="Project name")
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name="Region",
    )
    dayoff_limit = models.PositiveIntegerField(
        default=5,
        verbose_name="Monthly limit of days off",
        help_text=(
            "The maximum total number of days off an employee can take for this "
            "project in a single calendar month (taking into account all their "
            "requests for that month, excluding rejected ones)."
        ),
    )
    max_workers_per_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
        verbose_name="Employee limit as of the date (blank) - no restrictions (default).",
        help_text=(
            "The maximum number of employees on this project who can be off on the same day. "
            "Leave blank for no limit (default)."
        ),
    )
    coordinators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="coordinated_projects",
        limit_choices_to={"is_staff": True},
        blank=True,
        verbose_name="Responsible coordinators",
    )

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        unique_together = ("name", "region")
        ordering = ["region__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.region})"


class ProjectDateLimit(models.Model):
    """
    Redefining the employee limit for a project on a SPECIFIC date.
    If there is no entry here for the date, the general `Project.max_workers_per_day` applies
    (and if that is also empty, there are no limits at all for that date).
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="date_limits",
        verbose_name="Project",
    )
    date = models.DateField(verbose_name="Date")
    max_workers = models.PositiveIntegerField(
        verbose_name="Employee limit for this date"
    )

    class Meta:
        verbose_name = "Employee limit for this date"
        verbose_name_plural = "Staffing limits for specific dates"
        unique_together = ("project", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.project} — {self.date}: {self.max_workers}"


class EmailRecipientType(models.TextChoices):
    TO = "to", "Direct recipient (To)"
    CC = "cc", "Copy (DW/CC)"


class ProjectEmailRecipient(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="email_recipients",
        verbose_name="Project",
    )
    email = models.EmailField(verbose_name="Email")
    recipient_type = models.CharField(
        max_length=2,
        choices=EmailRecipientType.choices,
        default=EmailRecipientType.TO,
        verbose_name="Sending type",
    )

    class Meta:
        verbose_name = "Project email recipient"
        verbose_name_plural = "Project email recipients"

    def __str__(self):
        return f"{self.email} ({self.get_recipient_type_display()})"


class RequestType(models.TextChoices):
    DAYOFF = "dayoff", "Day off"
    L4 = "l4", "Sick day (L4)"


class RequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class AbsenceRequest(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requests",
        verbose_name="Worker",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="requests",
        verbose_name="Project",
    )
    request_type = models.CharField(
        max_length=10, choices=RequestType.choices, verbose_name="Type"
    )
    start_date = models.DateField(verbose_name="Start date")
    end_date = models.DateField(verbose_name="End date")
    days_count = models.PositiveIntegerField(verbose_name="Number of days")
    status = models.CharField(
        max_length=10,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        verbose_name="Status",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    decided_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Date of decision"
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="decided_requests",
        verbose_name="Who made the decision?",
    )

    # {coordinator's telegram_id: message_id of the sent push notification}
    notified_coordinator_message_ids = models.JSONField(default=dict, blank=True)
    dates = models.JSONField(
        default=list, blank=True, verbose_name="Selected dates (ISO)"
    )

    class Meta:
        verbose_name = "Reporting"
        verbose_name_plural = "Reporting"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.get_request_type_display()} ({self.start_date}–{self.end_date})"

    def can_be_rejected(self) -> bool:
        # Deviation is blocked for L4.
        return self.request_type == RequestType.DAYOFF


class RecurrenceType(models.TextChoices):
    NONE = "none", "None (one-time)"
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"


class BroadcastAudience(models.TextChoices):
    ALL = "all", "All active users"
    SPECIFIC = "specific", "Selected Users"


WEEKDAY_CHOICES = [
    (0, "Monday"),
    (1, "Tuesday"),
    (2, "Wednesday"),
    (3, "Thursday"),
    (4, "Friday"),
    (5, "Saturday"),
    (6, "Sunday"),
]


class Broadcast(models.Model):
    """
    The broadcast notifies employees via a Telegram bot—either as a one-time event
    (scheduled for a specific date and time) or on a recurring basis (daily, weekly, or monthly).
    The actual sending is performed by the `send_broadcast_message` Celery task,
    while the check to see if it is time to send is handled by the periodic task
    `check_and_send_due_broadcasts` (via Celery Beat, every 5 minutes).
    """

    title = models.CharField(max_length=200, verbose_name="Name (for the admin panel)")
    text = models.TextField(
        verbose_name="Message text",
        help_text=(
            "Supports emojis and basic Telegram HTML formatting: "
            "<b>bold</b>, <i>italics</i>"
        ),
    )

    audience = models.CharField(
        max_length=23,
        choices=BroadcastAudience.choices,
        default=BroadcastAudience.ALL,
        verbose_name="Recipients",
    )
    specific_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="broadcasts",
        verbose_name="Selected users",
        help_text="Fill this out only if “Selected users” is selected above.",
    )

    recurrence = models.CharField(
        max_length=23,
        choices=RecurrenceType.choices,
        default=RecurrenceType.NONE,
        verbose_name="Repetition",
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date and time of departure (for a one-time trip)",
    )
    send_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Departure time (for scheduled flights)",
    )
    weekday = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=WEEKDAY_CHOICES,
        verbose_name="Day of the week (for “Every Week”)",
    )
    day_of_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        verbose_name="Month number (for “Monthly”)",
        help_text="If a month has fewer days (e.g., 31 in February), it will be sent on the last day of the month.",
    )

    is_active = models.BooleanField(default=True, verbose_name="Active")
    last_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Last sent")
    last_sent_count = models.PositiveIntegerField(
        default=0, verbose_name="Sent successfully (last time)"
    )
    last_failed_count = models.PositiveIntegerField(
        default=0, verbose_name="Mistakes (for the last time)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Newsletter"
        verbose_name_plural = "Newsletters"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_recipients(self):
        from users.models import User

        if self.audience == BroadcastAudience.SPECIFIC:
            return self.specific_users.filter(is_active=True, telegram_id__isnull=False)
        return User.objects.filter(is_active=True, telegram_id__isnull=False)

    def _same_period(self, last, now):
        if self.recurrence == RecurrenceType.DAILY:
            return last.date() == now.date()
        if self.recurrence == RecurrenceType.WEEKLY:
            return last.isocalendar()[:2] == now.isocalendar()[:2]
        if self.recurrence == RecurrenceType.MONTHLY:
            return (last.year, last.month) == (now.year, now.month)
        return False

    def is_due(self, now) -> bool:
        """Is it time to send out this newsletter right now"""
        if self.recurrence == RecurrenceType.NONE:
            return (
                bool(self.scheduled_at)
                and self.scheduled_at <= now
                and self.last_sent_at is None
            )

        if not self.send_time:
            return False
        if self.last_sent_at and self._same_period(self.last_sent_at, now):
            return False
        if now.time() < self.send_time:
            return False

        if self.recurrence == RecurrenceType.DAILY:
            return True
        if self.recurrence == RecurrenceType.WEEKLY:
            return self.weekday is not None and now.weekday() == self.weekday
        if self.recurrence == RecurrenceType.MONTHLY:
            if self.day_of_month is None:
                return False
            last_day = cal_module.monthrange(now.year, now.month)[1]
            effective_day = min(self.day_of_month, last_day)
            return now.day == effective_day
        return False


def generate_decision_token():
    return secrets.token_urlsafe(32)


class RequestDepartment(models.TextChoices):
    ADMINISTRATION = "administration", "Administration"
    ACCOUNTING = "accounting", "Accounting Department"


class DepartmentResponsiblePerson(models.Model):
    """
    Who receives an email upon a new submission to the administration/accounting department —
    analogous to ProjectEmailRecipient, but linked to the User profile (the email
    is always taken from the current user.email) rather than an arbitrary address.
    """

    department = models.CharField(
        max_length=20,
        choices=RequestDepartment.choices,
        verbose_name="Department",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"is_staff": True},
        related_name="department_responsibilities",
        verbose_name="Person in charge",
    )
    recipient_type = models.CharField(
        max_length=2,
        choices=EmailRecipientType.choices,
        default=EmailRecipientType.TO,
        verbose_name="Sending type",
    )

    class Meta:
        verbose_name = "Department contact person"
        verbose_name_plural = "Departmental points of contact"
        unique_together = ("department", "user", "recipient_type")

    def __str__(self):
        return f"{self.get_department_display()} — {self.user} ({self.get_recipient_type_display()})"


class ServiceRequest(models.Model):
    """
    Submission to administration (documents) or the accounting department
    (salary-related questions). Unlike an AbsenceRequest, this does not
    involve dates or a project—only free-text input. The decision (Accept/Reject)
    is made not within the bot, but directly via email using a link containing
    a unique `decision_token`.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_requests",
    )
    request_type = models.CharField(
        max_length=20, choices=RequestDepartment.choices, verbose_name="Тип"
    )
    text = models.TextField(verbose_name="Text of the request")
    status = models.CharField(
        max_length=10,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        verbose_name="Status",
    )
    decision_token = models.CharField(
        max_length=64, unique=True, default=generate_decision_token, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Reporting to Administration/Accounting"
        verbose_name_plural = "Reporting to Administration/Accounting"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_request_type_display()} — {self.user} ({self.status})"


class SickLeaveDocument(models.Model):
    """
    Скан або фото лікарняного (L4), прикріплене працівником у Mini App.

    Вміст зберігається в Postgres, а не на диску: на Railway у кожного сервісу
    свій тимчасовий диск, тож файл, збережений сервісом web, не побачив би
    worker, який надсилає лист. Після відправки і терміну зберігання
    (SICK_LEAVE_FILE_RETENTION_DAYS) вміст очищується автоматично, запис лишається.
    """

    request = models.ForeignKey(
        AbsenceRequest,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Request",
    )
    filename = models.CharField(max_length=255, verbose_name="File name")
    content_type = models.CharField(max_length=100, verbose_name="Content type")
    size = models.PositiveIntegerField(verbose_name="Size (bytes)")
    content = models.BinaryField(null=True, blank=True, editable=False)
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Uploaded")
    emailed_at = models.DateTimeField(null=True, blank=True, verbose_name="Emailed")
    purged_at = models.DateTimeField(null=True, blank=True, verbose_name="File removed")

    class Meta:
        verbose_name = "Sick leave document"
        verbose_name_plural = "Sick leave documents"
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"{self.filename} ({self.request})"

