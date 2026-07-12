from django.contrib import admin
from django.http import HttpRequest

from scenes.models import MutationOperation, SceneSearchProjection


@admin.register(MutationOperation)
class MutationOperationAdmin(admin.ModelAdmin):
    list_display = ("operation_type", "source", "created_at")
    list_filter = ("operation_type", "source", "created_at")
    ordering = ("-created_at",)
    readonly_fields = tuple(field.name for field in MutationOperation._meta.fields)
    search_fields: tuple[str, ...] = ()

    def has_view_permission(
        self, request: HttpRequest, obj: MutationOperation | None = None
    ) -> bool:
        del obj
        return bool(request.user.is_active and request.user.is_staff)

    def has_add_permission(self, request: HttpRequest) -> bool:
        del request
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: MutationOperation | None = None
    ) -> bool:
        del request, obj
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: MutationOperation | None = None
    ) -> bool:
        del request, obj
        return False


@admin.register(SceneSearchProjection)
class SceneSearchProjectionAdmin(admin.ModelAdmin):
    list_display = (
        "source_scene_version",
        "projection_schema_version",
        "search_configuration_version",
        "built_at",
    )
    list_filter = ("projection_schema_version", "search_configuration_version", "built_at")
    readonly_fields = tuple(field.name for field in SceneSearchProjection._meta.fields)
    search_fields: tuple[str, ...] = ()

    def has_view_permission(
        self, request: HttpRequest, obj: SceneSearchProjection | None = None
    ) -> bool:
        del obj
        return bool(request.user.is_active and request.user.is_staff)

    def has_add_permission(self, request: HttpRequest) -> bool:
        del request
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: SceneSearchProjection | None = None
    ) -> bool:
        del request, obj
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: SceneSearchProjection | None = None
    ) -> bool:
        del request, obj
        return False
