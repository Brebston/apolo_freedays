from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

# Only Latin letters and hyphens; no numbers or special characters.
latin_name_validator = RegexValidator(
    regex=r"^[A-Za-z\-]+$",
    message="Only Latin letters are allowed (no numbers or special characters)..",
)


class Language(models.TextChoices):
    UK = "uk", "Українська"
    PL = "pl", "Polski"
    EN = "en", "English"
    RU = "ru", "Русский"


class User(AbstractUser):
    """
    Custom user model.
    Registration and login take place via a bot (email + password) rather than
    the standard Django username form, so the username is auto-generated from the email.
    """

    telegram_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Telegram ID",
    )
    first_name = models.CharField(
        max_length=100,
        validators=[latin_name_validator],
        verbose_name="Name",
    )
    last_name = models.CharField(
        max_length=100,
        validators=[latin_name_validator],
        verbose_name="Surname",
    )
    email = models.EmailField(unique=True, blank=True, null=True, verbose_name="Email")
    phone = models.CharField(max_length=32, blank=True, verbose_name="Phone number")
    language = models.CharField(
        max_length=2,
        choices=Language.choices,
        default=Language.UK,
        verbose_name="Interface language",
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email or f"tg{self.telegram_id or ''}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.email})"
