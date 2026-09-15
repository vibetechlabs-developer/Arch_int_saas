from django.contrib import admin

from apps.site_visits.models import SiteVisit


@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = ("__str__", "company", "lead", "project", "assigned_to", "visit_date", "is_completed", "is_deleted")
    list_filter = ("company", "deleted_at")
    search_fields = ("address", "notes")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "client", "report_submitted_at")

    def is_deleted(self, obj: SiteVisit) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def is_completed(self, obj: SiteVisit) -> bool:
        return obj.is_completed

    is_completed.boolean = True
    is_completed.short_description = "Completed"

    def get_queryset(self, request):
        return SiteVisit.all_objects.all()
