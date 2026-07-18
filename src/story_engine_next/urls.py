from django.urls import path

from story_engine_next import views

urlpatterns = [
    path("story-engine-next/<path:route>", views.app_shell, name="story-engine-next-route"),
    path("story-engine-next/", views.app_shell, name="story-engine-next"),
    path("api/story-engine-next/dashboard/", views.dashboard_api),
    path("api/story-engine-next/brainstorm/", views.brainstorm_collection_api),
    path("api/story-engine-next/brainstorm/<uuid:session_id>/", views.brainstorm_api),
    path("api/story-engine-next/brainstorm/<uuid:session_id>/draw/", views.brainstorm_draw_api),
    path("api/story-engine-next/brainstorm/<uuid:session_id>/cards/", views.brainstorm_card_api),
    path(
        "api/story-engine-next/brainstorm/<uuid:session_id>/cards/<uuid:selection_id>/",
        views.brainstorm_card_api,
    ),
    path(
        "api/story-engine-next/brainstorm/<uuid:session_id>/generate/",
        views.brainstorm_generate_api,
    ),
    path(
        "api/story-engine-next/suggestions/<uuid:suggestion_id>/apply/", views.apply_suggestion_api
    ),
    path("api/story-engine-next/chat/", views.chat_collection_api),
    path("api/story-engine-next/chat/<uuid:session_id>/", views.chat_api),
    path("api/story-engine-next/chat/<uuid:session_id>/messages/", views.chat_message_api),
    path("api/story-engine-next/characters/", views.character_collection_api),
    path("api/story-engine-next/characters/<uuid:character_id>/", views.character_api),
    path("api/story-engine-next/characters/<uuid:character_id>/fill/", views.character_fill_api),
    path(
        "api/story-engine-next/characters/<uuid:character_id>/assist/", views.character_assist_api
    ),
    path(
        "api/story-engine-next/characters/<uuid:character_id>/mechanics/<uuid:membership_id>/borrow/",
        views.character_borrow_api,
    ),
    path(
        "api/story-engine-next/characters/<uuid:character_id>/mechanics/<uuid:membership_id>/borrow/<uuid:log_id>/",
        views.character_borrow_api,
    ),
    path("api/story-engine-next/family/", views.family_api),
    path("api/story-engine-next/relationship-web/", views.relationship_web_api),
    path("api/story-engine-next/world-bible/", views.world_bible_api),
    path("api/story-engine-next/world-bible/<uuid:entry_id>/", views.world_bible_entry_api),
    path("api/story-engine-next/world/", views.world_api),
    path("api/story-engine-next/story/", views.story_api),
    path("api/story-engine-next/story/<uuid:chapter_id>/", views.chapter_api),
    path("api/story-engine-next/story/<uuid:chapter_id>/stage/", views.chapter_stage_api),
    path("api/story-engine-next/scenes/<uuid:scene_id>/save/", views.scene_save_api),
    path("api/story-engine-next/modules/<str:kind>/", views.module_api),
    path("api/story-engine-next/search/", views.search_api),
]
