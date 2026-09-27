from datetime import date, timedelta

from django.template.response import TemplateResponse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import filesizeformat
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.http import content_disposition_header
from django.contrib import admin
from django.utils import timezone
from django import forms

from core.admin_widgets import EmojiTextarea
from core.models import (
    AbsenceRequest,
    Project,
    ProjectDateLimit,
    ProjectEmailRecipient,
    Region,
    Broadcast,
    DepartmentResponsiblePerson,
    ServiceRequest,
    SickLeaveDocument,
)
from core.tasks import notify_worker_telegram
from core.models import INACTIVE_STATUSES, RequestStatus


class ProjectEmailRecipientInline(admin.TabularInline):
    model = ProjectEmailRecipient
    extra = 1


class ProjectDateLimitInline(admin.TabularInline):
    model = ProjectDateLimit
    extra = 1
    verbose_name = "Date limit"
    verbose_name_plural = "Employee limits for specific dates (override)"


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "region",
        "dayoff_limit",
        "max_workers_per_day",
        "coordinators_list",
    )
    list_filter = ("region",)
    search_fields = ("name",)
    filter_horizontal = ("coordinators",)
    inlines = [ProjectEmailRecipientInline]

    @admin.display(description="Coordinators")
    def coordinators_list(self, obj):
        return ", ".join(str(c) for c in obj.coordinators.all())


class SickLeaveDocumentInline(admin.TabularInline):
    model = SickLeaveDocument
    extra = 0
    can_delete = False
    fields = ("download", "size_display", "uploaded_at", "emailed_at", "purged_at")
    readonly_fields = fields
    verbose_name = "Sick leave document"
    verbose_name_plural = "Sick leave documents (L4)"

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="File")
    def download(self, obj):
        if obj.content is None:
            return f"{obj.filename} (removed after retention period)"
        url = reverse("admin:core_absencerequest_document_download", args=[obj.request_id, obj.id])
        return format_html('<a href="{}">⬇ {}</a>', url, obj.filename)

    @admin.display(description="Size")
    def size_display(self, obj):
        return filesizeformat(obj.size)


@admin.register(AbsenceRequest)
class AbsenceRequestAdmin(admin.ModelAdmin):
    inlines = [SickLeaveDocumentInline]

    def get_urls(self):
        custom = [
            path(
                "<int:request_id>/documents/<int:document_id>/download/",
                self.admin_site.admin_view(self.download_document),
                name="core_absencerequest_document_download",
            ),
            path(
                "statistics-export/",
                self.admin_site.admin_view(self.statistics_export),
                name="core_absencerequest_statistics_export",
            ),
        ]
        return custom + super().get_urls()

    change_list_template = "admin/core/absencerequest/change_list.html"

    def statistics_export(self, request):
        """Форма експорту статистики в Excel і сама генерація файлу."""
        if not self.has_view_permission(request):
            raise PermissionDenied
        today = timezone.localdate()
        default_from = (today.replace(day=1) - timedelta(days=330)).replace(day=1)
        default_to = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Statistics export (Excel)",
            "projects": Project.objects.select_related("region").order_by("name"),
            "date_from": request.GET.get("date_from", default_from.isoformat()),
            "date_to": request.GET.get("date_to", default_to.isoformat()),
            "selected_project": request.GET.get("project", ""),
            "selected_lang": request.GET.get("lang", "en"),
        }
        if "download" not in request.GET:
            return TemplateResponse(request, "admin/core/absencerequest/statistics_export.html", context)

        try:
            date_from = date.fromisoformat(context["date_from"])
            date_to = date.fromisoformat(context["date_to"])
        except ValueError:
            context["error"] = "Enter valid dates."
            return TemplateResponse(request, "admin/core/absencerequest/statistics_export.html", context)
        if date_from > date_to:
            context["error"] = "The start date must be before the end date."
            return TemplateResponse(request, "admin/core/absencerequest/statistics_export.html", context)
        if (date_to - date_from).days > 3 * 366:
            context["error"] = "The period can be at most 3 years."
            return TemplateResponse(request, "admin/core/absencerequest/statistics_export.html", context)

        project = Project.objects.filter(id=context["selected_project"]).first() if context["selected_project"].isdigit() else None
        workbook = build_statistics_workbook(date_from, date_to, project, context["selected_lang"])
        filename = f"absence_statistics_{date_from:%Y-%m-%d}_{date_to:%Y-%m-%d}.xlsx"
        response = HttpResponse(
            workbook, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = content_disposition_header(True, filename)
        return response

    def download_document(self, request, request_id, document_id):
        if not self.has_view_permission(request):
            raise PermissionDenied
        doc = get_object_or_404(SickLeaveDocument, id=document_id, request_id=request_id, content__isnull=False)
        response = HttpResponse(bytes(doc.content), content_type=doc.content_type)
        response["Content-Disposition"] = content_disposition_header(True, doc.filename)
        return response

    list_display = (
        "id",
        "user",
        "project",
        "request_type",
        "start_date",
        "end_date",
        "days_count",
        "status",
        "created_at",
        "decided_by",
    )
    list_filter = ("status", "request_type", "project__region", "project")
    search_fields = ("user__first_name", "user__last_name", "user__email")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "notified_coordinator_message_ids", "dates")

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = (
                AbsenceRequest.objects.filter(pk=obj.pk)
                .values_list("status", flat=True)
                .first()
            )

        if obj.request_type == "l4" and obj.status == RequestStatus.REJECTED:
            obj.status = RequestStatus.APPROVED

        super().save_model(request, obj, form, change)

        status_changed = (
            change
            and old_status == RequestStatus.PENDING
            and obj.status != RequestStatus.PENDING
        )
        if status_changed:
            if not obj.decided_at:
                obj.decided_at = timezone.now()
            if not obj.decided_by_id:
                obj.decided_by = request.user
            obj.save(update_fields=["decided_at", "decided_by"])
            notify_worker_telegram.delay(obj.id)


@admin.register(ProjectDateLimit)
class ProjectDateLimitAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "date", "max_workers")
    list_filter = ("project",)
    date_hierarchy = "date"
    search_fields = ("project__name",)


class BroadcastAdminForm(forms.ModelForm):
    class Meta:
        model = Broadcast
        fields = "__all__"
        widgets = {"text": EmojiTextarea()}


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    form = BroadcastAdminForm

    list_display = (
        "id",
        "title",
        "audience",
        "recurrence",
        "scheduled_at",
        "send_time",
        "is_active",
        "last_sent_at",
        "last_sent_count",
        "last_failed_count",
    )
    list_filter = ("audience", "recurrence", "is_active")
    search_fields = ("title", "text")
    filter_horizontal = ("specific_users",)
    readonly_fields = ("last_sent_at", "last_sent_count", "last_failed_count")
    actions = ["send_now"]

    fieldsets = (
        (None, {"fields": ("title", "text")}),
        ("Recipients", {"fields": ("audience", "specific_users")}),
        (
            "Schedule",
            {
                "fields": (
                    "recurrence",
                    "scheduled_at",
                    "send_time",
                    "weekday",
                    "day_of_month",
                    "is_active",
                ),
                "description": (
                    "For a one-time shipment, leave “Repeat” set to “None” and specify"
                    "the exact date and time in the “Date and Time of Sending” field. For a regular mailing"
                    "select the recurrence type and specify the “Sending Time” (+ day of the week/month)."
                ),
            },
        ),
        (
            "Statistics for the Last Shipment",
            {"fields": ("last_sent_at", "last_sent_count", "last_failed_count")},
        ),
    )

    @admin.action(description="📤 Send the selected newsletters now")
    def send_now(self, request, queryset):
        from core.tasks import send_broadcast_message

        count = 0
        for broadcast in queryset:
            send_broadcast_message.delay(broadcast.id)
            count += 1
        self.message_user(
            request, f"Placed in the queue for immediate shipment: {count}"
        )


@admin.register(DepartmentResponsiblePerson)
class DepartmentResponsiblePersonAdmin(admin.ModelAdmin):
    list_display = ("id", "department", "user", "recipient_type")
    list_filter = ("department", "recipient_type")


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "request_type", "status", "created_at", "decided_at")
    list_filter = ("request_type", "status")
    search_fields = ("user__first_name", "user__last_name", "text")
    readonly_fields = ("decision_token", "created_at")
    date_hierarchy = "created_at"



def build_statistics_workbook(date_from, date_to, project, lang):
    """Збирає дані з бази у прості структури і передає в core.stats_export."""
    from core.services import request_dates
    from core.stats_export import build_workbook

    absences_qs = (
        AbsenceRequest.objects.select_related("user", "project", "project__region")
        .prefetch_related("documents")
        .filter(start_date__lte=date_to, end_date__gte=date_from)
    )
    service_qs = ServiceRequest.objects.select_related("user").filter(
        created_at__date__gte=date_from, created_at__date__lte=date_to,
    )
    if project is not None:
        absences_qs = absences_qs.filter(project=project)

    absences, days = [], []
    for req in absences_qs:
        worker = f"{req.user.last_name} {req.user.first_name}".strip()
        absences.append({
            "id": req.id,
            "created": timezone.localtime(req.created_at).replace(tzinfo=None),
            "worker": worker,
            "project": req.project.name,
            "region": req.project.region.name,
            "type": req.request_type,
            "status": req.status,
            "start": req.start_date,
            "end": req.end_date,
            "days": req.days_count,
            "sick_note": bool(req.documents.all()),
        })
        if req.status not in INACTIVE_STATUSES:
            days.extend(
                {"date": d, "worker": worker, "project": req.project.name, "type": req.request_type}
                for d in request_dates(req) if date_from <= d <= date_to
            )

    service = [
        {
            "id": sr.id,
            "created": timezone.localtime(sr.created_at).replace(tzinfo=None),
            "worker": f"{sr.user.last_name} {sr.user.first_name}".strip(),
            "department": sr.request_type,
            "status": sr.status,
            "text": sr.text,
        }
        for sr in service_qs
    ]
    return build_workbook(
        absences=absences, days=days, service_requests=service, date_from=date_from, date_to=date_to,
        project_label=project.name if project else None, lang=lang,
    )
