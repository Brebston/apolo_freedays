from django.conf import settings
from django.db import models


class Region(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва регіону")

    class Meta:
        verbose_name = "Регіон"
        verbose_name_plural = "Регіони"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=150, verbose_name="Назва проєкту")
    region = models.ForeignKey(
        Region, on_delete=models.CASCADE, related_name="projects", verbose_name="Регіон",
    )
    dayoff_limit = models.PositiveIntegerField(
        default=5, verbose_name="Ліміт днів (вихідні)",
        help_text="Максимальна кількість вихідних днів, яку можна обрати в одному зголошенні.",
    )
    coordinators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="coordinated_projects",
        limit_choices_to={"is_staff": True},
        blank=True,
        verbose_name="Відповідальні координатори",
    )

    class Meta:
        verbose_name = "Проєкт"
        verbose_name_plural = "Проєкти"
        unique_together = ("name", "region")
        ordering = ["region__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.region})"


class EmailRecipientType(models.TextChoices):
    TO = "to", "Прямий отримувач (To)"
    CC = "cc", "Копія (DW/CC)"


class ProjectEmailRecipient(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="email_recipients", verbose_name="Проєкт",
    )
    email = models.EmailField(verbose_name="Email")
    recipient_type = models.CharField(
        max_length=2, choices=EmailRecipientType.choices,
        default=EmailRecipientType.TO, verbose_name="Тип надсилання",
    )

    class Meta:
        verbose_name = "Email-отримувач проєкту"
        verbose_name_plural = "Email-отримувачі проєктів"

    def __str__(self):
        return f"{self.email} ({self.get_recipient_type_display()})"


class RequestType(models.TextChoices):
    DAYOFF = "dayoff", "Вихідний день"
    L4 = "l4", "Лікарняний (L4)"


class RequestStatus(models.TextChoices):
    PENDING = "pending", "Очікує"
    APPROVED = "approved", "Підтверджено"
    REJECTED = "rejected", "Відхилено"


class AbsenceRequest(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="requests", verbose_name="Працівник",
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="requests", verbose_name="Проєкт",
    )
    request_type = models.CharField(max_length=10, choices=RequestType.choices, verbose_name="Тип")
    start_date = models.DateField(verbose_name="Дата початку")
    end_date = models.DateField(verbose_name="Дата закінчення")
    days_count = models.PositiveIntegerField(verbose_name="Кількість днів")
    status = models.CharField(
        max_length=10, choices=RequestStatus.choices, default=RequestStatus.PENDING, verbose_name="Статус",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата рішення")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="decided_requests", verbose_name="Хто прийняв рішення",
    )
    # {telegram_id координатора: message_id надісланого push-повідомлення}
    notified_coordinator_message_ids = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Зголошення"
        verbose_name_plural = "Зголошення"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.get_request_type_display()} ({self.start_date}–{self.end_date})"

    def can_be_rejected(self) -> bool:
        # Для L4 відхилення заблоковане згідно з п.4.4.2 / п.6 ТЗ
        return self.request_type == RequestType.DAYOFF
