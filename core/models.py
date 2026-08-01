from django.conf import settings
from django.db import models


class Region(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва регіону")

    class Meta:
        verbose_name = "Region"
        verbose_name_plural = "Regions"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=150, verbose_name="Project name")
    region = models.ForeignKey(
        Region, on_delete=models.CASCADE, related_name="projects", verbose_name="Region",
    )
    dayoff_limit = models.PositiveIntegerField(
        default=5, verbose_name="Limit on days off",
        help_text="The maximum number of days off that can be selected in a single request.",
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


class EmailRecipientType(models.TextChoices):
    TO = "to", "Direct recipient (To)"
    CC = "cc", "Copy (DW/CC)"


class ProjectEmailRecipient(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="email_recipients", verbose_name="Project",
    )
    email = models.EmailField(verbose_name="Email")
    recipient_type = models.CharField(
        max_length=2, choices=EmailRecipientType.choices,
        default=EmailRecipientType.TO, verbose_name="Sending type",
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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="requests", verbose_name="Worker",
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="requests", verbose_name="Project",
    )
    request_type = models.CharField(max_length=10, choices=RequestType.choices, verbose_name="Type")
    start_date = models.DateField(verbose_name="Start date")
    end_date = models.DateField(verbose_name="End date")
    days_count = models.PositiveIntegerField(verbose_name="Number of days")
    status = models.CharField(
        max_length=10, choices=RequestStatus.choices, default=RequestStatus.PENDING, verbose_name="Status",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name="Date of decision")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="decided_requests", verbose_name="Who made the decision?",
    )

    # {coordinator's telegram_id: message_id of the sent push notification}
    notified_coordinator_message_ids = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Reporting"
        verbose_name_plural = "Reporting"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.get_request_type_display()} ({self.start_date}–{self.end_date})"

    def can_be_rejected(self) -> bool:
        # Deviation is blocked for L4.
        return self.request_type == RequestType.DAYOFF
