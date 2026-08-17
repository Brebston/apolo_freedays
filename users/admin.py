from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "id",
        "last_name",
        "first_name",
        "email",
        "phone",
        "telegram_id",
        "language",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_active", "language")
    search_fields = ("first_name", "last_name", "email", "phone", "telegram_id")
    ordering = ("last_name", "first_name")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal data",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "language",
                    "telegram_id",
                )
            },
        ),
        (
            "Access",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "description": (
                    "is_active = access to the Telegram bot (without it, the user will receive "
                    'an "access denied" message). is_staff = coordinator (access to the '
                    "coordinator panel in the bot and permission to log in to the Django Admin)."
                ),
            },
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "telegram_id",
                    "email",
                    "phone",
                    "password1",
                    "password2",
                    "is_staff",
                ),
            },
        ),
    )
