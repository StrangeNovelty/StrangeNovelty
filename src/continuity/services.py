from django.core.exceptions import ValidationError


def validate_story_scope(record, workspace, work=None):
    if record and record.workspace_id != workspace.id:
        raise ValidationError("Record must belong to this Workspace.")
    if record and work and getattr(record, "work_id", None) and record.work_id != work.id:
        raise ValidationError("Record must belong to this Work.")


def validate_continuity_record(record):
    workspace, work = record.workspace, getattr(record, "work", None)
    for name in (
        "character",
        "secret",
        "thread",
        "character_subject",
        "group_subject",
        "location",
        "region",
        "codex",
        "item",
        "creature",
        "chapter",
        "scene",
    ):
        validate_story_scope(getattr(record, name, None), workspace, work)
    if (
        getattr(record, "chapter_id", None)
        and getattr(record, "scene_id", None)
        and record.scene.chapter_id
        and record.scene.chapter_id != record.chapter_id
    ):
        raise ValidationError("Scene must belong to the selected Chapter.")
