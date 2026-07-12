import uuid
from typing import cast

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from accounts.managers import AccountManager


class Account(AbstractBaseUser, PermissionsMixin):
    """Project-owned human identity; not Workspace authorization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now, editable=False)

    objects = AccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:  # noqa: DJ012
        ordering = ("email",)
        verbose_name = "account"
        verbose_name_plural = "accounts"

    def __str__(self) -> str:
        return cast(str, self.email)


class WebAuthnCredential(models.Model):
    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="webauthn_credentials"
    )
    credential_id = models.BinaryField(unique=True)
    public_key = models.BinaryField()
    sign_count = models.PositiveBigIntegerField(default=0)
    transports = models.CharField(max_length=64, blank=True, default="")
    device_type = models.CharField(max_length=24, blank=True, default="")
    backed_up = models.BooleanField(default=False)
    user_verified = models.BooleanField(default=True)
    label = models.CharField(max_length=80)
    state = models.CharField(max_length=16, choices=State.choices, default=State.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"WebAuthn Credential {self.id}"

    class Meta:  # noqa: DJ012
        constraints = [
            models.CheckConstraint(
                condition=models.Q(state__in=("active", "revoked")),
                name="webauthn_credential_state_valid",
            )
        ]


class TOTPCredential(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="totp_credentials")
    encrypted_secret = models.BinaryField()
    label = models.CharField(max_length=80)
    algorithm = models.CharField(max_length=8, default="SHA1")
    digits = models.PositiveSmallIntegerField(default=6)
    period = models.PositiveSmallIntegerField(default=30)
    last_used_counter = models.BigIntegerField(null=True, blank=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"TOTP Credential {self.id}"

    class Meta:  # noqa: DJ012
        constraints = [
            models.CheckConstraint(
                condition=models.Q(state__in=("pending", "active", "revoked")),
                name="totp_credential_state_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(algorithm="SHA1", digits=6, period=30),
                name="totp_parameters_v1_valid",
            ),
        ]


class RecoveryCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="recovery_codes")
    generation_id = models.UUIDField()
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # noqa: DJ012
        indexes = [
            models.Index(fields=("account", "generation_id"), name="recovery_generation_idx")
        ]

    def __str__(self) -> str:
        return f"Recovery Code {self.id}"


class SessionAssurance(models.Model):
    class Level(models.TextChoices):
        PASSWORD = "password", "Password"
        MFA = "mfa", "MFA"

    class Method(models.TextChoices):
        NONE = "", "None"
        WEBAUTHN = "webauthn", "WebAuthn"
        TOTP = "totp", "TOTP"
        RECOVERY_CODE = "recovery_code", "Recovery code"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="session_assurances"
    )
    session_digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    password_authenticated_at = models.DateTimeField()
    mfa_authenticated_at = models.DateTimeField(null=True, blank=True)
    recent_authenticated_at = models.DateTimeField(null=True, blank=True)
    assurance_level = models.CharField(max_length=16, choices=Level.choices, default=Level.PASSWORD)
    mfa_method = models.CharField(max_length=16, choices=Method.choices, blank=True, default="")
    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason = models.CharField(max_length=24, blank=True, default="")

    def __str__(self) -> str:
        return f"Session Assurance {self.id}"

    class Meta:  # noqa: DJ012
        constraints = [
            models.CheckConstraint(
                condition=models.Q(assurance_level__in=("password", "mfa")),
                name="session_assurance_level_valid",
            )
        ]


class AuthenticationChallenge(models.Model):
    class Purpose(models.TextChoices):
        WEBAUTHN_REGISTER = "webauthn_register", "WebAuthn registration"
        WEBAUTHN_AUTHENTICATE = "webauthn_authenticate", "WebAuthn authentication"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="auth_challenges")
    session_digest = models.CharField(max_length=64)
    purpose = models.CharField(max_length=24, choices=Purpose.choices)
    encrypted_challenge = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Authentication Challenge {self.id}"

    class Meta:  # noqa: DJ012
        constraints = [
            models.CheckConstraint(
                condition=models.Q(purpose__in=("webauthn_register", "webauthn_authenticate")),
                name="authentication_challenge_purpose_valid",
            )
        ]


class AuthenticationThrottle(models.Model):
    class Category(models.TextChoices):
        PASSWORD = "password", "Password"
        WEBAUTHN = "webauthn", "WebAuthn"
        TOTP = "totp", "TOTP"
        RECOVERY = "recovery", "Recovery"
        REAUTHENTICATION = "reauthentication", "Reauthentication"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    keyed_digest = models.CharField(max_length=64)
    category = models.CharField(max_length=24, choices=Category.choices)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    window_started_at = models.DateTimeField()
    blocked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("keyed_digest", "category"), name="unique_auth_throttle_scope"
            )
        ]

    def __str__(self) -> str:
        return f"Authentication Throttle {self.id}"


class RecoveryEnrollment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="recovery_enrollments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Recovery Enrollment {self.id}"
