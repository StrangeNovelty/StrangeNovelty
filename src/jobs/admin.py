from django.contrib import admin
from django.http import HttpRequest

from jobs.models import IdempotencyRecord, Job, JobAttempt


class ReadOnlyOperationalAdmin(admin.ModelAdmin):
    def has_view_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        del obj
        return bool(request.user.is_active and request.user.is_staff)

    def has_add_permission(self, request: HttpRequest) -> bool:
        del request
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        del request, obj
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        del request, obj
        return False


@admin.register(Job)
class JobAdmin(ReadOnlyOperationalAdmin):
    list_display = ("job_type", "state", "attempt_count", "available_at", "updated_at")
    list_filter = ("job_type", "state", "effect_class", "result", "failure")
    readonly_fields = tuple(field.name for field in Job._meta.fields)
    search_fields: tuple[str, ...] = ()


@admin.register(JobAttempt)
class JobAttemptAdmin(ReadOnlyOperationalAdmin):
    list_display = ("outcome", "attempt_number", "started_at", "finished_at")
    list_filter = ("outcome", "error_category")
    readonly_fields = tuple(field.name for field in JobAttempt._meta.fields)
    search_fields: tuple[str, ...] = ()


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(ReadOnlyOperationalAdmin):
    list_display = ("operation", "caller", "state", "result_classification", "created_at")
    list_filter = ("operation", "caller", "state", "result_classification")
    readonly_fields = tuple(field.name for field in IdempotencyRecord._meta.fields)
    search_fields: tuple[str, ...] = ()
