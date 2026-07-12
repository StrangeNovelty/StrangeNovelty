from django.contrib import admin
from django.http import HttpRequest

from security_events.models import SecurityEvent


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "outcome",
        "target_category",
        "service_role",
        "reason",
        "occurred_at",
    )
    list_filter = ("event_type", "outcome", "target_category", "service_role", "occurred_at")
    ordering = ("-occurred_at",)
    readonly_fields = tuple(field.name for field in SecurityEvent._meta.fields)
    search_fields: tuple[str, ...] = ()

    def has_view_permission(self, request: HttpRequest, obj: SecurityEvent | None = None) -> bool:
        del obj
        return bool(request.user.is_active and request.user.is_staff)

    def has_add_permission(self, request: HttpRequest) -> bool:
        del request
        return False

    def has_change_permission(self, request: HttpRequest, obj: SecurityEvent | None = None) -> bool:
        del request, obj
        return False

    def has_delete_permission(self, request: HttpRequest, obj: SecurityEvent | None = None) -> bool:
        del request, obj
        return False
