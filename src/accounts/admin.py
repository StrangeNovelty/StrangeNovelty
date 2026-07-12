from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.forms import AccountChangeAdminForm, AccountCreationAdminForm
from accounts.models import (
    Account,
    AuthenticationChallenge,
    AuthenticationThrottle,
    RecoveryCode,
    RecoveryEnrollment,
    SessionAssurance,
    TOTPCredential,
    WebAuthnCredential,
)


@admin.register(Account)
class AccountAdmin(UserAdmin):
    """Operational Account administration; never Workspace authorization."""

    form = AccountChangeAdminForm
    add_form = AccountCreationAdminForm
    model = Account

    ordering = ("email",)
    list_display = ("email", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email",)
    readonly_fields = ("id", "date_joined", "last_login")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            "Django administration",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Timestamps", {"fields": ("last_login", "date_joined")}),
    )


class ReadOnlySecurityAdmin(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff if obj is None else False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WebAuthnCredential)
class WebAuthnCredentialAdmin(ReadOnlySecurityAdmin):
    list_display = ("id", "state", "created_at", "last_used_at")
    exclude = ("credential_id", "public_key")


@admin.register(TOTPCredential)
class TOTPCredentialAdmin(ReadOnlySecurityAdmin):
    list_display = ("id", "state", "created_at", "last_used_at")
    exclude = ("encrypted_secret",)


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(ReadOnlySecurityAdmin):
    list_display = ("id", "created_at", "used_at", "revoked_at")
    exclude = ("code_hash",)


@admin.register(SessionAssurance)
class SessionAssuranceAdmin(ReadOnlySecurityAdmin):
    list_display = ("id", "assurance_level", "mfa_method", "created_at", "revoked_at")
    exclude = ("session_digest",)


for model in (AuthenticationChallenge, AuthenticationThrottle, RecoveryEnrollment):
    admin.site.register(model, ReadOnlySecurityAdmin)
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )
