from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .csv_import import TEMPLATE_CSV, parse_csv

from .forms import UserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm

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
    readonly_fields = ("username",)

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
                    "an 'access denied' message). is_staff = coordinator (access to "
                    "the coordinator panel in the bot and permission to log in to Django Admin)."
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

    change_list_template = "admin/users/user/change_list.html"

    def get_urls(self):
        custom = [
            path("import-csv/", self.admin_site.admin_view(self.import_csv), name="users_user_import_csv"),
            path(
                "import-csv/template/",
                self.admin_site.admin_view(self.import_csv_template),
                name="users_user_import_csv_template",
            ),
        ]
        return custom + super().get_urls()

    def import_csv(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        context = {**self.admin_site.each_context(request), "opts": self.model._meta, "title": "Import workers from CSV"}

        if request.method == "POST" and request.POST.get("step") == "confirm":
            stored = request.session.get(SESSION_KEY)
            if not stored:
                messages.error(request, "The preview has expired. Please upload the file again.")
                return redirect("admin:users_user_import_csv")
            created = updated = 0
            with transaction.atomic():
                for item in stored["plan"]:
                    if item["action"] == "create":
                        user = User(
                            first_name=item["first_name"], last_name=item["last_name"],
                            phone=item["phone"], telegram_id=item["telegram_id"], is_active=True,
                        )
                        user.set_unusable_password()
                        user.save()
                        created += 1
                    elif item["action"] == "update":
                        User.objects.filter(telegram_id=item["telegram_id"]).update(
                            first_name=item["first_name"], last_name=item["last_name"], phone=item["phone"],
                        )
                        updated += 1
            del request.session[SESSION_KEY]
            messages.success(request, f"Import finished: {created} created, {updated} updated.")
            return redirect("admin:users_user_changelist")

        if request.method == "POST":
            upload = request.FILES.get("file")
            if upload is None:
                context["upload_error"] = "Choose a CSV file."
            elif upload.size > MAX_UPLOAD_BYTES:
                context["upload_error"] = "The file is larger than 2 MB."
            else:
                parsed, file_errors = parse_csv(upload.read())
                if file_errors:
                    context["upload_error"] = " ".join(file_errors)
                else:
                    update_existing = bool(request.POST.get("update_existing"))
                    plan = _plan_rows(parsed, update_existing)
                    request.session[SESSION_KEY] = {"plan": plan}
                    counts = {key: sum(1 for i in plan if i["action"] == key)
                              for key in ("create", "update", "unchanged", "skip", "error")}
                    context.update({"plan": plan, "counts": counts, "filename": upload.name,
                                    "can_import": counts["create"] + counts["update"] > 0})
        return TemplateResponse(request, "admin/users/user/import_csv.html", context)

    def import_csv_template(self, request):
        response = HttpResponse("\ufeff" + TEMPLATE_CSV, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="workers_import_template.csv"'
        return response


# --- Масовий імпорт працівників з CSV ---------------------------------------

SESSION_KEY = "users_csv_import"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024


def _plan_rows(parsed, update_existing):
    """Для кожного валідного рядка визначає дію: create / update / unchanged / skip."""
    ids = [row.telegram_id for row in parsed if row.ok]
    existing = {u.telegram_id: u for u in User.objects.filter(telegram_id__in=ids)}
    plan = []
    for row in parsed:
        item = {
            "line": row.line, "first_name": row.first_name, "last_name": row.last_name,
            "phone": row.phone, "telegram_id": row.telegram_id, "errors": row.errors,
        }
        if not row.ok:
            item["action"] = "error"
        elif row.telegram_id in existing:
            user = existing[row.telegram_id]
            same = (user.first_name, user.last_name, user.phone) == (row.first_name, row.last_name, row.phone)
            item["action"] = "unchanged" if same else ("update" if update_existing else "skip")
            item["current"] = f"{user.last_name} {user.first_name} {user.phone}".strip()
        else:
            item["action"] = "create"
        plan.append(item)
    return plan
