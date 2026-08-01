from django.contrib import admin

from .models import AbsenceRequest, Project, ProjectEmailRecipient, Region


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
    readonly_fields = ("created_at", "notified_coordinator_message_ids")
