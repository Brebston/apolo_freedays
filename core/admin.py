from django.contrib import admin
from django.utils import timezone

from core.models import AbsenceRequest, Project, ProjectEmailRecipient, Region
from core.tasks import notify_worker_telegram
from core.models import RequestStatus


class ProjectEmailRecipientInline(admin.TabularInline):
    model = ProjectEmailRecipient
    extra = 1


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "region", "dayoff_limit", "coordinators_list")
    list_filter = ("region",)
    search_fields = ("name",)
    filter_horizontal = ("coordinators",)
    inlines = [ProjectEmailRecipientInline]

    @admin.display(description="Координатори")
    def coordinators_list(self, obj):
        return ", ".join(str(c) for c in obj.coordinators.all())


@admin.register(AbsenceRequest)
class AbsenceRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "project", "request_type", "start_date", "end_date",
        "days_count", "status", "created_at", "decided_by",
    )
    list_filter = ("status", "request_type", "project__region", "project")
    search_fields = ("user__first_name", "user__last_name", "user__email")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "notified_coordinator_message_ids", "dates")
    
    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = AbsenceRequest.objects.filter(pk=obj.pk).values_list("status", flat=True).first()

        if obj.request_type == "l4" and obj.status == RequestStatus.REJECTED:
            obj.status = RequestStatus.APPROVED

        super().save_model(request, obj, form, change)

        status_changed = change and old_status == RequestStatus.PENDING and obj.status != RequestStatus.PENDING
        if status_changed:
            if not obj.decided_at:
                obj.decided_at = timezone.now()
            if not obj.decided_by_id:
                obj.decided_by = request.user
            obj.save(update_fields=["decided_at", "decided_by"])
            notify_worker_telegram.delay(obj.id)
