"""Root URL configuration with no private application routes yet."""

from django.contrib import admin
from django.urls import path

from accounts.views import (
    WorkspaceLoginView,
    WorkspaceLogoutView,
    mfa_challenge,
    password_change,
    recovery_code_verify,
    recovery_codes_regenerate,
    revoke_other_sessions,
    revoke_session,
    security_home,
    totp_confirm,
    totp_enroll,
    totp_revoke,
    webauthn_auth_complete,
    webauthn_auth_options,
    webauthn_register_complete,
    webauthn_register_options,
    webauthn_revoke,
)
from ai_assistance.views import (
    ai_request_status,
    apply_ai_suggestion,
    cancel_ai_request_view,
    expire_ai_suggestion,
    reject_ai_suggestion,
    request_ai_suggestion,
    review_ai_suggestion,
)
from characters.views import (
    character_create,
    character_detail,
    character_list,
    character_scene_link,
    character_scene_unlink,
    scene_characters_update,
)
from operations.health import liveness, readiness
from scenes.search_views import scene_search
from scenes.views import scene_create, scene_editor, scene_list, scene_save
from workspaces.views import root, workspace_home

urlpatterns = [
    path("", root, name="root"),
    path("login/", WorkspaceLoginView.as_view(), name="login"),
    path("logout/", WorkspaceLogoutView.as_view(), name="logout"),
    path("mfa/", mfa_challenge, name="mfa-challenge"),
    path("mfa/webauthn/options/", webauthn_auth_options, name="webauthn-auth-options"),
    path("mfa/webauthn/complete/", webauthn_auth_complete, name="webauthn-auth-complete"),
    path("mfa/recovery/", recovery_code_verify, name="recovery-code-verify"),
    path("account/security/", security_home, name="account-security"),
    path(
        "account/security/webauthn/options/",
        webauthn_register_options,
        name="webauthn-register-options",
    ),
    path(
        "account/security/webauthn/complete/",
        webauthn_register_complete,
        name="webauthn-register-complete",
    ),
    path("account/security/totp/", totp_enroll, name="totp-enroll"),
    path("account/security/totp/confirm/", totp_confirm, name="totp-confirm"),
    path("account/security/totp/<uuid:credential_id>/revoke/", totp_revoke, name="totp-revoke"),
    path(
        "account/security/webauthn/<uuid:credential_id>/revoke/",
        webauthn_revoke,
        name="webauthn-revoke",
    ),
    path(
        "account/security/recovery-codes/",
        recovery_codes_regenerate,
        name="recovery-codes-regenerate",
    ),
    path(
        "account/security/sessions/<uuid:assurance_id>/revoke/",
        revoke_session,
        name="session-revoke",
    ),
    path(
        "account/security/sessions/revoke-others/",
        revoke_other_sessions,
        name="sessions-revoke-others",
    ),
    path("account/security/password/", password_change, name="password-change"),
    path("workspace/", workspace_home, name="workspace-home"),
    path("scenes/", scene_list, name="scene-list"),
    path("scenes/new/", scene_create, name="scene-create"),
    path("scenes/<uuid:scene_id>/", scene_editor, name="scene-editor"),
    path("scenes/<uuid:scene_id>/save/", scene_save, name="scene-save"),
    path(
        "scenes/<uuid:scene_id>/characters/",
        scene_characters_update,
        name="scene-characters-update",
    ),
    path("scenes/<uuid:scene_id>/ai/request/", request_ai_suggestion, name="ai-request"),
    path("ai/requests/<uuid:request_id>/", ai_request_status, name="ai-request-status"),
    path("ai/requests/<uuid:request_id>/cancel/", cancel_ai_request_view, name="ai-request-cancel"),
    path("ai/suggestions/<uuid:suggestion_id>/", review_ai_suggestion, name="ai-suggestion-review"),
    path(
        "ai/suggestions/<uuid:suggestion_id>/apply/",
        apply_ai_suggestion,
        name="ai-suggestion-apply",
    ),
    path(
        "ai/suggestions/<uuid:suggestion_id>/reject/",
        reject_ai_suggestion,
        name="ai-suggestion-reject",
    ),
    path(
        "ai/suggestions/<uuid:suggestion_id>/expire/",
        expire_ai_suggestion,
        name="ai-suggestion-expire",
    ),
    path("search/", scene_search, name="scene-search"),
    path("characters/", character_list, name="character-list"),
    path("characters/new/", character_create, name="character-create"),
    path(
        "characters/<uuid:character_id>/",
        character_detail,
        name="character-detail",
    ),
    path(
        "characters/<uuid:character_id>/scenes/",
        character_scene_link,
        name="character-scene-link",
    ),
    path(
        "characters/<uuid:character_id>/scenes/<uuid:scene_id>/unlink/",
        character_scene_unlink,
        name="character-scene-unlink",
    ),
    path("admin/", admin.site.urls),
    path("health/live/", liveness, name="health-live"),
    path("health/ready/", readiness, name="health-ready"),
    path("health/", liveness, name="health"),
]
