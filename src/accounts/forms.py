from typing import Any

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm

from accounts.models import Account


class EmailAuthenticationForm(AuthenticationForm):
    """Authenticate with normalized email while keeping failures generic."""

    username = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    error_messages = {
        "invalid_login": "Unable to sign in with those credentials.",
        "inactive": "Unable to sign in with those credentials.",
    }

    def clean_username(self) -> str:
        return Account.objects.normalize_login_email(self.cleaned_data["username"])


class AccountCreationAdminForm(UserCreationForm):
    """Supported password-handling form for operational Account creation."""

    class Meta(UserCreationForm.Meta):
        model = Account
        fields = ("email",)

    def clean_email(self) -> str:
        return Account.objects.normalize_login_email(self.cleaned_data["email"])


class AccountChangeAdminForm(UserChangeForm):
    """Supported password-hash display form for operational Account changes."""

    class Meta(UserChangeForm.Meta):
        model = Account
        fields = (
            "email",
            "password",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )

    def clean_email(self) -> str:
        return Account.objects.normalize_login_email(self.cleaned_data["email"])

    def clean_password(self) -> Any:
        return self.initial.get("password")
