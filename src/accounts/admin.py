from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.forms import AccountChangeAdminForm, AccountCreationAdminForm
from accounts.models import Account


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
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )
