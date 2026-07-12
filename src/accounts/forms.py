from typing import Any

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from accounts.models import Account
from accounts.throttling import is_blocked


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

    def clean(self) -> dict[str, Any]:
        attempted = self.data.get("username", "").strip().casefold()
        if is_blocked("password", f"login:{attempted}"):
            raise forms.ValidationError(self.error_messages["invalid_login"], code="invalid_login")
        return dict(super().clean())


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


class MfaCodeForm(forms.Form):
    code = forms.CharField(
        max_length=32, strip=True, widget=forms.TextInput(attrs={"autocomplete": "one-time-code"})
    )


class TotpEnrollmentForm(forms.Form):
    label = forms.CharField(max_length=80, initial="Authenticator app")


class RecoveryCodeForm(forms.Form):
    code = forms.CharField(
        max_length=32,
        strip=True,
        widget=forms.PasswordInput(attrs={"autocomplete": "one-time-code"}),
    )


class AccountPasswordChangeForm(PasswordChangeForm):
    pass
