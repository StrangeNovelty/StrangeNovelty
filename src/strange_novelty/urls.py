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
    ability_create,
    ability_delete_view,
    ability_detail,
    ability_event_create,
    ability_event_delete,
    ability_event_edit,
    ability_prediction_create,
    ability_prediction_delete,
    ability_prediction_edit,
    ability_stage_create,
    ability_stage_delete,
    ability_stage_edit,
    character_create,
    character_detail,
    character_group_create,
    character_group_delete_view,
    character_group_detail,
    character_group_list,
    character_list,
    character_relationship_create,
    character_relationship_delete_view,
    character_relationship_edit,
    character_scene_link,
    character_scene_unlink,
    group_membership_create,
    group_membership_delete,
    group_membership_edit,
    group_relationship_create,
    scene_characters_update,
)
from continuity.views import (
    child_create,
    continuity_home,
    knowledge_create,
    secret_detail,
    secret_transition,
    thread_create,
    thread_detail,
    thread_edit,
    thread_link_create,
    thread_list,
    thread_transition,
)
from decks.views import (
    active_toggle,
    card_library,
    cue_symbol_update,
    custom_card_create,
    deck_detail,
    deck_home,
    draw_action,
    draw_card_action,
    draw_conversion,
    draw_create,
    draw_detail,
    draw_interpretation,
    draw_list,
    favorite_toggle,
    review_action,
    review_card,
    review_dashboard,
    review_render,
)
from decks.views import (
    card_detail as deck_card_detail,
)
from decks.views import (
    guidance as deck_guidance,
)
from decks.views import (
    journal_detail as deck_journal_detail,
)
from decks.views import (
    spread_detail as deck_spread_detail,
)
from operations.health import liveness, readiness
from scenes.search_views import scene_search
from scenes.views import (
    scene_create,
    scene_editor,
    scene_list,
    scene_placement_update,
    scene_save,
)
from stories.views import (
    arc_create_view,
    arc_edit_view,
    chapter_create_view,
    chapter_detail,
    chapter_scene_attach,
    chapter_scene_create,
    chapter_scene_detach,
    chapter_scene_order,
    structure_delete_view,
    volume_create_view,
    volume_edit_view,
    work_create,
    work_detail,
    work_list,
)
from timeline.views import (
    cross_reference_view,
    event_create,
    event_detail,
    event_edit,
    event_link,
    event_transition,
    reader_order,
    relation_create,
    timeline_create,
    timeline_detail,
    timeline_edit,
    timeline_home,
    timeline_transition,
)
from workspaces.views import root, workspace_home
from worldbuilding.views import (
    record_connection_create,
    scene_world_context_update,
    world_home,
)
from worldbuilding.views import (
    record_create as world_record_create,
)
from worldbuilding.views import (
    record_delete as world_record_delete,
)
from worldbuilding.views import (
    record_detail as world_record_detail,
)
from worldbuilding.views import (
    record_list as world_record_list,
)

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
    path("continuity/", continuity_home, name="continuity-home"),
    path("timelines/", timeline_home, name="timeline-home"),
    path("timelines/new/", timeline_create, name="timeline-create"),
    path("timelines/cross-reference/", cross_reference_view, name="timeline-cross-reference"),
    path("timelines/reader-order/<uuid:work_id>/", reader_order, name="timeline-reader-order"),
    path("timelines/<uuid:timeline_id>/", timeline_detail, name="timeline-detail"),
    path("timelines/<uuid:timeline_id>/edit/", timeline_edit, name="timeline-edit"),
    path(
        "timelines/<uuid:timeline_id>/transition/", timeline_transition, name="timeline-transition"
    ),
    path("timelines/<uuid:timeline_id>/events/new/", event_create, name="timeline-event-create"),
    path("timeline-events/<uuid:event_id>/", event_detail, name="timeline-event-detail"),
    path(
        "timeline-events/<uuid:event_id>/edit/<str:section>/",
        event_edit,
        name="timeline-event-edit",
    ),
    path(
        "timeline-events/<uuid:event_id>/transition/",
        event_transition,
        name="timeline-event-transition",
    ),
    path(
        "timeline-events/<uuid:event_id>/links/<str:kind>/", event_link, name="timeline-event-link"
    ),
    path(
        "timeline-events/<uuid:event_id>/relations/",
        relation_create,
        name="timeline-relation-create",
    ),
    path("continuity/threads/", thread_list, name="continuity-thread-list"),
    path("continuity/threads/new/", thread_create, name="continuity-thread-create"),
    path("continuity/threads/<uuid:thread_id>/", thread_detail, name="continuity-thread-detail"),
    path(
        "continuity/threads/<uuid:thread_id>/edit/<str:section>/",
        thread_edit,
        name="continuity-thread-edit",
    ),
    path(
        "continuity/threads/<uuid:thread_id>/transition/",
        thread_transition,
        name="continuity-thread-transition",
    ),
    path(
        "continuity/threads/<uuid:thread_id>/<str:kind>/new/",
        child_create,
        name="continuity-child-create",
    ),
    path(
        "continuity/threads/<uuid:thread_id>/links/<str:kind>/",
        thread_link_create,
        name="continuity-thread-link-create",
    ),
    path(
        "continuity/knowledge/<str:kind>/new/", knowledge_create, name="continuity-knowledge-create"
    ),
    path("continuity/secrets/<uuid:secret_id>/", secret_detail, name="continuity-secret-detail"),
    path(
        "continuity/secrets/<uuid:secret_id>/transition/",
        secret_transition,
        name="continuity-secret-transition",
    ),
    path("decks/", deck_home, name="deck-home"),
    path("decks/draws/", draw_list, name="deck-draw-list"),
    path("decks/draws/new/", draw_create, name="deck-draw-create"),
    path("decks/draws/<uuid:draw_id>/", draw_detail, name="deck-draw-detail"),
    path("decks/draws/<uuid:draw_id>/action/", draw_action, name="deck-draw-action"),
    path(
        "decks/draws/cards/<uuid:draw_card_id>/action/",
        draw_card_action,
        name="deck-draw-card-action",
    ),
    path(
        "decks/draws/<uuid:draw_id>/interpretation/",
        draw_interpretation,
        name="deck-draw-interpretation",
    ),
    path(
        "decks/interpretations/<uuid:interpretation_id>/convert/",
        draw_conversion,
        name="deck-draw-conversion",
    ),
    path("decks/cards/", card_library, name="deck-card-library"),
    path("decks/cards/new/", custom_card_create, name="deck-custom-card-create"),
    path("decks/cards/<uuid:card_id>/", deck_card_detail, name="deck-card-detail"),
    path("decks/cards/<uuid:card_id>/favorite/", favorite_toggle, name="deck-favorite-toggle"),
    path("decks/cards/<uuid:card_id>/active/", active_toggle, name="deck-active-toggle"),
    path("decks/review/", review_dashboard, name="deck-review-dashboard"),
    path("decks/review/<uuid:card_id>/", review_card, name="deck-review-card"),
    path("decks/review/<uuid:card_id>/action/", review_action, name="deck-review-action"),
    path("decks/review/<uuid:card_id>/source/", review_render, name="deck-review-render"),
    path(
        "decks/review/cues/<uuid:cue_id>/symbol/", cue_symbol_update, name="deck-cue-symbol-update"
    ),
    path("decks/how-to-use/", deck_guidance, name="deck-guidance"),
    path("decks/spreads/<uuid:spread_id>/", deck_spread_detail, name="deck-spread-detail"),
    path("decks/journals/<uuid:journal_id>/", deck_journal_detail, name="deck-journal-detail"),
    path("decks/<uuid:deck_id>/", deck_detail, name="deck-detail"),
    path("world/", world_home, name="world-home"),
    path("world/<str:kind>/", world_record_list, name="world-record-list"),
    path("world/<str:kind>/new/", world_record_create, name="world-record-create"),
    path(
        "world/<str:kind>/<uuid:record_id>/",
        world_record_detail,
        name="world-record-detail",
    ),
    path(
        "world/<str:kind>/<uuid:record_id>/delete/",
        world_record_delete,
        name="world-record-delete",
    ),
    path(
        "world/<str:kind>/<uuid:record_id>/connections/",
        record_connection_create,
        name="world-record-connection-create",
    ),
    path("works/", work_list, name="work-list"),
    path("works/new/", work_create, name="work-create"),
    path("works/<uuid:work_id>/", work_detail, name="work-detail"),
    path(
        "works/<uuid:work_id>/delete/",
        structure_delete_view,
        {"record_kind": "work"},
        name="work-delete",
    ),
    path("works/<uuid:work_id>/volumes/new/", volume_create_view, name="volume-create"),
    path(
        "works/<uuid:work_id>/volumes/<uuid:volume_id>/",
        volume_edit_view,
        name="volume-edit",
    ),
    path(
        "works/<uuid:work_id>/volumes/<uuid:record_id>/delete/",
        structure_delete_view,
        {"record_kind": "volume"},
        name="volume-delete",
    ),
    path("works/<uuid:work_id>/arcs/new/", arc_create_view, name="arc-create"),
    path(
        "works/<uuid:work_id>/arcs/<uuid:arc_id>/",
        arc_edit_view,
        name="arc-edit",
    ),
    path(
        "works/<uuid:work_id>/arcs/<uuid:record_id>/delete/",
        structure_delete_view,
        {"record_kind": "arc"},
        name="arc-delete",
    ),
    path("works/<uuid:work_id>/chapters/new/", chapter_create_view, name="chapter-create"),
    path(
        "works/<uuid:work_id>/chapters/<uuid:chapter_id>/",
        chapter_detail,
        name="chapter-detail",
    ),
    path(
        "works/<uuid:work_id>/chapters/<uuid:record_id>/delete/",
        structure_delete_view,
        {"record_kind": "chapter"},
        name="chapter-delete",
    ),
    path(
        "works/<uuid:work_id>/chapters/<uuid:chapter_id>/scenes/new/",
        chapter_scene_create,
        name="chapter-scene-create",
    ),
    path(
        "works/<uuid:work_id>/chapters/<uuid:chapter_id>/scenes/attach/",
        chapter_scene_attach,
        name="chapter-scene-attach",
    ),
    path(
        "works/<uuid:work_id>/chapters/<uuid:chapter_id>/scenes/<uuid:scene_id>/order/",
        chapter_scene_order,
        name="chapter-scene-order",
    ),
    path(
        "works/<uuid:work_id>/chapters/<uuid:chapter_id>/scenes/<uuid:scene_id>/detach/",
        chapter_scene_detach,
        name="chapter-scene-detach",
    ),
    path("scenes/", scene_list, name="scene-list"),
    path("scenes/new/", scene_create, name="scene-create"),
    path("scenes/<uuid:scene_id>/", scene_editor, name="scene-editor"),
    path(
        "scenes/<uuid:scene_id>/world-context/",
        scene_world_context_update,
        name="scene-world-context-update",
    ),
    path("scenes/<uuid:scene_id>/save/", scene_save, name="scene-save"),
    path(
        "scenes/<uuid:scene_id>/placement/",
        scene_placement_update,
        name="scene-placement-update",
    ),
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
    path("groups/", character_group_list, name="character-group-list"),
    path("groups/new/", character_group_create, name="character-group-create"),
    path(
        "groups/<uuid:group_id>/",
        character_group_detail,
        name="character-group-detail",
    ),
    path(
        "groups/<uuid:group_id>/delete/",
        character_group_delete_view,
        name="character-group-delete",
    ),
    path(
        "groups/<uuid:group_id>/members/new/",
        group_membership_create,
        name="group-membership-create",
    ),
    path(
        "groups/<uuid:group_id>/relationships/new/",
        group_relationship_create,
        name="group-relationship-create",
    ),
    path(
        "groups/<uuid:group_id>/members/<uuid:membership_id>/",
        group_membership_edit,
        name="group-membership-edit",
    ),
    path(
        "groups/<uuid:group_id>/members/<uuid:membership_id>/delete/",
        group_membership_delete,
        name="group-membership-delete",
    ),
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
        "characters/<uuid:character_id>/relationships/new/",
        character_relationship_create,
        name="character-relationship-create",
    ),
    path(
        "characters/<uuid:character_id>/relationships/<uuid:relationship_id>/",
        character_relationship_edit,
        name="character-relationship-edit",
    ),
    path(
        "characters/<uuid:character_id>/relationships/<uuid:relationship_id>/delete/",
        character_relationship_delete_view,
        name="character-relationship-delete",
    ),
    path(
        "characters/<uuid:character_id>/scenes/<uuid:scene_id>/unlink/",
        character_scene_unlink,
        name="character-scene-unlink",
    ),
    path(
        "characters/<uuid:character_id>/abilities/new/",
        ability_create,
        name="ability-create",
    ),
    path(
        "characters/<uuid:character_id>/abilities/<uuid:ability_id>/",
        ability_detail,
        name="ability-detail",
    ),
    path(
        "characters/<uuid:character_id>/abilities/<uuid:ability_id>/delete/",
        ability_delete_view,
        name="ability-delete",
    ),
    path(
        "characters/<uuid:character_id>/abilities/<uuid:ability_id>/stages/new/",
        ability_stage_create,
        name="ability-stage-create",
    ),
    path(
        "characters/<uuid:character_id>/abilities/<uuid:ability_id>/stages/<uuid:stage_id>/",
        ability_stage_edit,
        name="ability-stage-edit",
    ),
    path(
        "characters/<uuid:character_id>/abilities/<uuid:ability_id>/stages/<uuid:stage_id>/delete/",
        ability_stage_delete,
        name="ability-stage-delete",
    ),
    path(
        "characters/<uuid:character_id>/abilities/<uuid:ability_id>/events/new/",
        ability_event_create,
        name="ability-event-create",
    ),
    path(
        "characters/<uuid:character_id>/abilities/<uuid:ability_id>/events/<uuid:event_id>/",
        ability_event_edit,
        name="ability-event-edit",
    ),
    path(
        "characters/<uuid:character_id>/abilities/<uuid:ability_id>/events/<uuid:event_id>/delete/",
        ability_event_delete,
        name="ability-event-delete",
    ),
    path(
        "characters/<uuid:character_id>/abilities/<uuid:ability_id>/predictions/new/",
        ability_prediction_create,
        name="ability-prediction-create",
    ),
    path(
        "characters/<uuid:character_id>/abilities/<uuid:ability_id>/predictions/<uuid:prediction_id>/",
        ability_prediction_edit,
        name="ability-prediction-edit",
    ),
    path(
        "characters/<uuid:character_id>/abilities/<uuid:ability_id>/predictions/<uuid:prediction_id>/delete/",
        ability_prediction_delete,
        name="ability-prediction-delete",
    ),
    path("admin/", admin.site.urls),
    path("health/live/", liveness, name="health-live"),
    path("health/ready/", readiness, name="health-ready"),
    path("health/", liveness, name="health"),
]
