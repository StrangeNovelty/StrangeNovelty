from django.contrib import admin

from legacy_imports.models import (
    IdentityMapping,
    ImportBatch,
    ImportFinding,
    ImportProvenance,
    StagedRevision,
    StagedScene,
)


class ReadOnlyImportAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ImportBatch)
class ImportBatchAdmin(ReadOnlyImportAdmin):
    list_display = ("id", "source_system", "state", "accepted_count", "warning_count", "created_at")
    list_filter = ("source_system", "state")


@admin.register(StagedScene)
class StagedSceneAdmin(ReadOnlyImportAdmin):
    list_display = ("id", "batch", "status", "proposed_lifecycle", "proposed_ordering")


@admin.register(StagedRevision)
class StagedRevisionAdmin(ReadOnlyImportAdmin):
    exclude = ("content",)
    list_display = ("id", "batch", "proposed_revision_number", "chronology", "is_current")


@admin.register(ImportFinding)
class ImportFindingAdmin(ReadOnlyImportAdmin):
    list_display = ("id", "batch", "severity", "issue_code", "field_category")
    list_filter = ("severity", "issue_code")


@admin.register(IdentityMapping)
class IdentityMappingAdmin(ReadOnlyImportAdmin):
    list_display = ("id", "batch", "source_entity_type", "target_entity_type", "state")


@admin.register(ImportProvenance)
class ImportProvenanceAdmin(ReadOnlyImportAdmin):
    list_display = ("id", "batch", "transformation_version", "created_at")
