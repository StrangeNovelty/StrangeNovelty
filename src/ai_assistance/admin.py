from django.contrib import admin

from ai_assistance.models import (
    AIContextManifest,
    AIRequest,
    AISuggestion,
    AISuggestionApplication,
    ProviderEffect,
)


class ReadOnlyAIAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AIRequest)
class AIRequestAdmin(ReadOnlyAIAdmin):
    exclude = ("instruction", "instruction_hash", "request_fingerprint", "idempotency_key")
    list_display = ("capability", "state", "provider", "requested_model", "created_at")
    list_filter = ("capability", "state", "provider")


@admin.register(AISuggestion)
class AISuggestionAdmin(ReadOnlyAIAdmin):
    exclude = (
        "original_output",
        "review_text",
        "source_content_hash",
        "output_hash",
        "provider_operation_identifier",
    )
    list_display = ("state", "provider", "model_classification", "created_at")
    list_filter = ("state", "provider", "model_classification")


@admin.register(ProviderEffect)
class ProviderEffectAdmin(ReadOnlyAIAdmin):
    exclude = ("operation_identifier",)
    list_display = ("provider", "outcome", "requested_at", "acknowledged_at")
    list_filter = ("provider", "outcome")


admin.site.register(AIContextManifest, ReadOnlyAIAdmin)
admin.site.register(AISuggestionApplication, ReadOnlyAIAdmin)
