from enum import StrEnum


class SecurityEventType(StrEnum):
    OWNER_BOOTSTRAP_SUCCEEDED = "owner_bootstrap_succeeded"
    OWNER_BOOTSTRAP_REJECTED = "owner_bootstrap_rejected"
    LOGIN_SUCCEEDED = "login_succeeded"
    LOGIN_FAILED = "login_failed"
    LOGOUT_SUCCEEDED = "logout_succeeded"
    WORKSPACE_ACCESS_DENIED = "workspace_access_denied"
    SCENE_ACCESS_DENIED = "scene_access_denied"
    SCENE_SAVE_CONFLICT = "scene_save_conflict"
    SCENE_SAVE_KEY_CONFLICT = "scene_save_key_conflict"
    WEBAUTHN_ENROLLED = "webauthn_enrolled"
    WEBAUTHN_USED = "webauthn_used"
    WEBAUTHN_ANOMALY = "webauthn_anomaly"
    WEBAUTHN_REVOKED = "webauthn_revoked"
    TOTP_ENROLLED = "totp_enrolled"
    TOTP_USED = "totp_used"
    TOTP_REVOKED = "totp_revoked"
    RECOVERY_CODES_GENERATED = "recovery_codes_generated"
    RECOVERY_CODE_USED = "recovery_code_used"
    MFA_SUCCEEDED = "mfa_succeeded"
    MFA_FAILED = "mfa_failed"
    SESSION_REVOKED = "session_revoked"
    PASSWORD_CHANGED = "password_changed"
    OWNER_RECOVERY_INITIATED = "owner_recovery_initiated"
    AUTHENTICATION_THROTTLED = "authentication_throttled"


class SecurityOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    DENIED = "denied"
    CONFLICTED = "conflicted"
    FAILED = "failed"


class SecurityTargetCategory(StrEnum):
    AUTHENTICATION = "authentication"
    ACCOUNT = "account"
    SESSION = "session"
    WORKSPACE = "workspace"
    SCENE = "scene"
    BOOTSTRAP = "bootstrap"
    MFA_FACTOR = "mfa_factor"


class SecurityServiceRole(StrEnum):
    WEB = "web"
    OPERATOR = "operator"


class SecurityReason(StrEnum):
    NONE = ""
    INVALID_CREDENTIALS = "invalid_credentials"
    INACCESSIBLE = "inaccessible"
    INACTIVE_GRANT = "inactive_grant"
    OPTIMISTIC_CONCURRENCY = "optimistic_concurrency"
    IDEMPOTENCY_KEY_REUSE = "idempotency_key_reuse"
    EXISTING_STATE = "existing_state"
    INVALID_INPUT = "invalid_input"
    INVALID_MFA = "invalid_mfa"
    REPLAY = "replay"
    ANOMALOUS_COUNTER = "anomalous_counter"
    THROTTLED = "throttled"
    RECOVERY = "recovery"


EVENT_TYPE_CHOICES = tuple(
    (value.value, value.name.replace("_", " ").title()) for value in SecurityEventType
)
OUTCOME_CHOICES = tuple((value.value, value.name.title()) for value in SecurityOutcome)
TARGET_CHOICES = tuple(
    (value.value, value.name.replace("_", " ").title()) for value in SecurityTargetCategory
)
SERVICE_ROLE_CHOICES = tuple((value.value, value.name.title()) for value in SecurityServiceRole)
REASON_CHOICES = tuple(
    (value.value, "None" if value is SecurityReason.NONE else value.name.replace("_", " ").title())
    for value in SecurityReason
)
