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
)
from core.tasks import notify_worker_telegram
from core.models import RequestStatus


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


@admin.register(AbsenceRequest)
class AbsenceRequestAdmin(admin.ModelAdmin):
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
