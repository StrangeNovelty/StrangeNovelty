from django.db.models import Count, Max, Min, Q

from characters.models import CharacterScene
from continuity.models import CharacterKnowledgeRecord
from timeline.models import EventCharacterLink, EventLocationLink
from worldbuilding.models import SceneLocationLink


def relation_warnings(event):
    warnings = []
    for relation in event.outgoing_relations.select_related("target"):
        if (
            relation.relation_type == "before"
            and event.start_sort_value is not None
            and relation.target.start_sort_value is not None
            and event.start_sort_value > relation.target.start_sort_value
        ):
            warnings.append(f"Marked before {relation.target}, but sorted after it.")
        if (
            relation.relation_type == "after"
            and event.start_sort_value is not None
            and relation.target.start_sort_value is not None
            and event.start_sort_value < relation.target.start_sort_value
        ):
            warnings.append(f"Marked after {relation.target}, but sorted before it.")
    return warnings


def character_appearance_index(character):
    scenes = CharacterScene.objects.filter(character=character).select_related(
        "scene__chapter", "scene__work"
    )
    chronology = EventCharacterLink.objects.filter(character=character).aggregate(
        first=Min("event__start_sort_value"), latest=Max("event__start_sort_value")
    )
    return {
        "scene_count": scenes.values("scene").distinct().count(),
        "chapter_count": scenes.exclude(scene__chapter=None)
        .values("scene__chapter")
        .distinct()
        .count(),
        "pov_count": scenes.filter(scene__chapter__pov_character=character)
        .values("scene__chapter")
        .distinct()
        .count(),
        "first_reader": scenes.order_by(
            "scene__work__created_at", "scene__chapter__order", "scene__structure_order"
        ).first(),
        "latest_reader": scenes.order_by(
            "-scene__work__created_at", "-scene__chapter__order", "-scene__structure_order"
        ).first(),
        **chronology,
    }


def location_appearance_index(location):
    scenes = SceneLocationLink.objects.filter(location=location).select_related("scene__chapter")
    chronology = EventLocationLink.objects.filter(location=location).aggregate(
        first=Min("event__start_sort_value"), latest=Max("event__start_sort_value")
    )
    return {
        "scene_count": scenes.values("scene").distinct().count(),
        "chapter_count": scenes.exclude(scene__chapter=None)
        .values("scene__chapter")
        .distinct()
        .count(),
        **chronology,
    }


def world_appearance_index(record):
    manager_names = {
        "CharacterGroup": "scenegrouplink_links",
        "WorldItem": "sceneitemlink_links",
        "Creature": "scenecreaturelink_links",
    }
    manager = getattr(record, manager_names[record.__class__.__name__])
    links = manager.select_related("scene__chapter")
    event_links = record.timeline_links.select_related("event")
    return {
        "scene_count": links.values("scene").distinct().count(),
        "chapter_count": links.exclude(scene__chapter=None)
        .values("scene__chapter")
        .distinct()
        .count(),
        "first_chronology": event_links.aggregate(value=Min("event__start_sort_value"))["value"],
        "latest_chronology": event_links.aggregate(value=Max("event__start_sort_value"))["value"],
    }


def cross_reference(workspace, data):
    mode = data.get("mode", "characters")
    work_id = data.get("work")
    scenes = workspace.scenes.exclude(lifecycle="trashed").select_related("work", "chapter")
    if work_id:
        scenes = scenes.filter(work_id=work_id)
    selected = [value for value in data.getlist("characters") if value]
    if mode == "characters" and selected:
        if data.get("match") == "all":
            scenes = (
                scenes.filter(character_links__character_id__in=selected)
                .annotate(
                    selected_count=Count(
                        "character_links__character",
                        filter=Q(character_links__character_id__in=selected),
                        distinct=True,
                    )
                )
                .filter(selected_count=len(set(selected)))
            )
        else:
            scenes = scenes.filter(character_links__character_id__in=selected)
        if data.get("without"):
            scenes = scenes.exclude(character_links__character_id=data["without"])
        if data.get("pov") == "1":
            scenes = scenes.filter(chapter__pov_character_id__in=selected)
    if mode == "character_location":
        if selected:
            scenes = scenes.filter(character_links__character_id__in=selected)
        if data.get("location"):
            scenes = scenes.filter(scenelocationlink_links__location_id=data["location"])
    if mode == "group_members":
        scenes = scenes.filter(
            character_links__character__group_memberships__group_id=data.get("group")
        )
    if mode == "item_character":
        scenes = scenes.filter(sceneitemlink_links__item_id=data.get("item"))
        if selected:
            scenes = scenes.filter(character_links__character_id__in=selected)
    if mode == "creature_location":
        scenes = scenes.filter(scenecreaturelink_links__creature_id=data.get("creature"))
        if data.get("location"):
            scenes = scenes.filter(scenelocationlink_links__location_id=data["location"])
    if mode == "thread_character":
        scenes = scenes.filter(thread_links__thread_id=data.get("thread"))
        if selected:
            scenes = scenes.filter(character_links__character_id__in=selected)
    if mode == "chronology_range":
        if data.get("start"):
            scenes = scenes.filter(timeline_links__event__start_sort_value__gte=data["start"])
        if data.get("end"):
            scenes = scenes.filter(timeline_links__event__start_sort_value__lte=data["end"])
    return scenes.distinct().order_by(
        "work__title", "chapter__order", "structure_order", "ordering"
    )


def knowledge_cross_reference(workspace, secret_id):
    return CharacterKnowledgeRecord.objects.filter(
        workspace=workspace, secret_id=secret_id
    ).select_related("character", "chapter", "scene")
