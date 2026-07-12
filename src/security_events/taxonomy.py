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
