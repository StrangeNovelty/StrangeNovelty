from dataclasses import dataclass

from django.db.models import QuerySet

from characters.models import Character, CharacterGroup
from scenes.models import Scene
from stories.models import Chapter

READING_WORDS_PER_MINUTE = 250


@dataclass(frozen=True, slots=True)
class SceneWritingSummary:
    scene: Scene
    word_count: int


@dataclass(frozen=True, slots=True)
class ChapterWritingSummary:
    scenes: tuple[SceneWritingSummary, ...]
    scene_count: int
    word_count: int
    reading_minutes: int
    recent_scene: Scene | None
    cast: tuple[Character, ...]
    has_intake_brief: bool
    has_outline: bool
    locations: tuple[object, ...]
    groups: tuple[CharacterGroup, ...]
    items: tuple[object, ...]
    creatures: tuple[object, ...]


def summarize_chapter(chapter: Chapter) -> ChapterWritingSummary:
    scenes = tuple(_chapter_scenes(chapter))
    scene_summaries = tuple(
        SceneWritingSummary(
            scene=scene,
            word_count=_word_count(
                scene.current_revision.content if scene.current_revision else ""
            ),
        )
        for scene in scenes
    )
    total_words = sum(item.word_count for item in scene_summaries)
    recent_scene = max(scenes, key=lambda scene: scene.updated_at, default=None)
    cast = tuple(
        Character.objects.filter(
            workspace_id=chapter.workspace_id,
            scenes__chapter=chapter,
            scenes__lifecycle__in=(Scene.Lifecycle.ACTIVE, Scene.Lifecycle.ARCHIVED),
        )
        .distinct()
        .order_by("name", "id")
    )
    has_intake = any(
        value.strip()
        for value in (
            chapter.concept,
            chapter.goal,
            chapter.key_beats,
            chapter.emotional_arc,
            chapter.character_focus,
        )
    )
    from worldbuilding.models import Creature, Location, WorldItem

    scene_ids = tuple(scene.id for scene in scenes)
    locations = tuple(
        Location.objects.filter(scenelocationlink_links__scene_id__in=scene_ids)
        .distinct()
        .order_by("name", "id")
    )
    groups = tuple(
        CharacterGroup.objects.filter(scenegrouplink_links__scene_id__in=scene_ids)
        .distinct()
        .order_by("name", "id")
    )
    items = tuple(
        WorldItem.objects.filter(sceneitemlink_links__scene_id__in=scene_ids)
        .distinct()
        .order_by("name", "id")
    )
    creatures = tuple(
        Creature.objects.filter(scenecreaturelink_links__scene_id__in=scene_ids)
        .distinct()
        .order_by("name", "id")
    )
    return ChapterWritingSummary(
        scenes=scene_summaries,
        scene_count=len(scene_summaries),
        word_count=total_words,
        reading_minutes=max(
            1, (total_words + READING_WORDS_PER_MINUTE - 1) // READING_WORDS_PER_MINUTE
        )
        if total_words
        else 0,
        recent_scene=recent_scene,
        cast=cast,
        has_intake_brief=has_intake,
        has_outline=bool(chapter.outline.strip()),
        locations=locations,
        groups=groups,
        items=items,
        creatures=creatures,
    )


def _chapter_scenes(chapter: Chapter) -> QuerySet[Scene]:
    return (
        Scene.objects.filter(chapter=chapter)
        .exclude(lifecycle=Scene.Lifecycle.TRASHED)
        .select_related("current_revision")
        .prefetch_related("characters")
        .order_by("structure_order", "id")
    )


def _word_count(content: str) -> int:
    return len(content.split())
