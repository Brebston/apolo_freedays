from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

# Тільки латинські літери та дефіс, без цифр і спецсимволів (п.4.1, п.6 ТЗ)
latin_name_validator = RegexValidator(
    regex=r"^[A-Za-z\-]+$",
    message="Дозволені лише латинські літери (без цифр та спецсимволів).",
)


class Language(models.TextChoices):
    UK = "uk", "Українська"
    PL = "pl", "Polski"
    EN = "en", "English"
    RU = "ru", "Русский"


class User(AbstractUser):
    """
    Кастомна модель користувача.
    Реєстрація/вхід відбувається через бота (email + пароль), а не через
    стандартну Django username-форму, тому username автогенерується з email.
    """

    telegram_id = models.BigIntegerField(
        unique=True, null=True, blank=True, db_index=True,
        verbose_name="Telegram ID",
    )
    first_name = models.CharField(
        max_length=100, validators=[latin_name_validator], verbose_name="Ім'я",
    )
    last_name = models.CharField(
        max_length=100, validators=[latin_name_validator], verbose_name="Прізвище",
    )
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(max_length=32, blank=True, verbose_name="Телефон")
    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.UK,
        verbose_name="Мова інтерфейсу",
    )

    class Meta:
        verbose_name = "Користувач"
        verbose_name_plural = "Користувачі"

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.email})"
