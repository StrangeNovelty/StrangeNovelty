from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from stories.models import (
    PACING_SCORE_FIELDS,
    Chapter,
    ChapterPlanningSnapshot,
    WritingDelta,
)

PLANNING_FIELDS = (
    "concept",
    "goal",
    "key_beats",
    "emotional_arc",
    "character_focus",
    "brain_dump",
    "outline",
    "notes",
    "status",
    "editorial_concerns",
    "revision_priorities",
    "unresolved_questions",
    "final_check_notes",
)


def capture_planning_snapshot(chapter: Chapter, *, label: str, trigger: str = "manual"):
    beats = [
        {
            "order": beat.order,
            "title": beat.title,
            "beat_type": beat.beat_type,
            "summary": beat.summary,
            "purpose": beat.purpose,
            "pov_character_id": str(beat.pov_character_id) if beat.pov_character_id else None,
            "intended_scene_id": str(beat.intended_scene_id) if beat.intended_scene_id else None,
            "emotional_direction": beat.emotional_direction,
            "status": beat.status,
            "notes": beat.notes,
        }
        for beat in chapter.structured_beats.all()
    ]
    try:
        profile = chapter.pacing_profile
    except Exception:  # RelatedObjectDoesNotExist is awkward to import portably.
        pacing = {}
    else:
        pacing = {
            field: getattr(profile, field)
            for field in (
                *PACING_SCORE_FIELDS,
                *(f.replace("_score", "_notes") for f in PACING_SCORE_FIELDS),
            )
        }
    return ChapterPlanningSnapshot.objects.create(
        chapter=chapter,
        label=label.strip() or "Planning snapshot",
        trigger=trigger,
        planning_content={field: getattr(chapter, field) for field in PLANNING_FIELDS},
        beat_data=beats,
        pacing_data=pacing,
    )


@transaction.atomic
def restore_planning_snapshot(snapshot: ChapterPlanningSnapshot):
    chapter = Chapter.objects.select_for_update().get(id=snapshot.chapter_id)
    capture_planning_snapshot(
        chapter, label=f"Before restore: {snapshot.label}", trigger="before_restore"
    )
    for field in PLANNING_FIELDS:
        if field in snapshot.planning_content:
            setattr(chapter, field, snapshot.planning_content[field])
    chapter.full_clean()
    chapter.save(update_fields=(*PLANNING_FIELDS, "updated_at"))
    chapter.structured_beats.all().delete()
    from stories.models import ChapterBeat, ChapterPacingProfile

    for values in snapshot.beat_data:
        ChapterBeat.objects.create(chapter=chapter, **values)
    if snapshot.pacing_data:
        ChapterPacingProfile.objects.update_or_create(
            chapter=chapter, defaults=snapshot.pacing_data
        )
    return chapter


def record_writing_delta(*, scene, revision, previous_content: str = ""):
    previous_count = len(previous_content.split())
    resulting_count = len(revision.content.split())
    return WritingDelta.objects.get_or_create(
        revision=revision,
        defaults={
            "workspace": scene.workspace,
            "work": scene.work,
            "chapter": scene.chapter,
            "scene": scene,
            "activity_date": timezone.localdate(revision.created_at),
            "word_delta": max(resulting_count - previous_count, 0),
            "resulting_word_count": resulting_count,
        },
    )[0]


def writing_statistics(workspace, *, work=None, chapter=None):
    today = timezone.localdate()
    qs = WritingDelta.objects.filter(workspace=workspace)
    if work:
        qs = qs.filter(work=work)
    if chapter:
        qs = qs.filter(chapter=chapter)
    daily = {
        row["activity_date"]: row["total"] or 0
        for row in qs.filter(activity_date__gte=today - timedelta(days=6))
        .values("activity_date")
        .annotate(total=Sum("word_delta"))
    }
    streak = 0
    cursor = today
    while daily.get(cursor, 0) > 0:
        streak += 1
        cursor -= timedelta(days=1)
    return {
        "today": daily.get(today, 0),
        "week": sum(daily.values()),
        "streak": streak,
        "seven_days": [
            {
                "date": today - timedelta(days=offset),
                "words": daily.get(today - timedelta(days=offset), 0),
            }
            for offset in range(6, -1, -1)
        ],
    }


def chapter_progress(chapter: Chapter):
    scenes = chapter.scenes.exclude(lifecycle="trashed")
    return {
        "concept": bool(chapter.concept.strip()),
        "goal": bool(chapter.goal.strip()),
        "key_beats": bool(chapter.key_beats.strip()),
        "outline": bool(chapter.outline.strip()),
        "beats": chapter.structured_beats.exists(),
        "scenes": scenes.exists(),
        "briefs": any(scene.briefs.filter(status="active").exists() for scene in scenes),
        "pacing": hasattr(chapter, "pacing_profile"),
        "pov": bool(chapter.pov_character_id),
        "continuity": chapter.thread_links.exists(),
        "timeline": chapter.timeline_links.exists(),
    }
