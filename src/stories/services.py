import uuid
from collections.abc import Mapping
from typing import cast

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from accounts.models import Account
from scenes.exceptions import LifecycleDisallowsMutation
from scenes.models import Scene
from scenes.services import SceneMutationResult, create_scene
from stories.models import Arc, Chapter, Volume, Work
from workspaces.models import Workspace
from workspaces.services import get_authorized_workspace

ORDER_STEP = 1024


class StoryStructureError(Exception):
    pass


class StoryStructureInaccessible(StoryStructureError):
    pass


class StoryStructureConflict(StoryStructureError):
    pass


def create_work(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    values: Mapping[str, object],
) -> Work:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            work = Work(workspace=workspace, **values)
            work.full_clean()
            work.save()
            return work
    except (IntegrityError, ValidationError) as exc:
        raise StoryStructureConflict("Work could not be created.") from exc


def update_work(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    work_id: uuid.UUID,
    values: Mapping[str, object],
) -> Work:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            work = Work.objects.select_for_update().get(id=work_id, workspace=workspace)
            _apply_values(work, values)
            work.full_clean()
            work.save()
            return work
    except Work.DoesNotExist as exc:
        raise StoryStructureInaccessible("Work is unavailable.") from exc
    except (IntegrityError, ValidationError) as exc:
        raise StoryStructureConflict("Work could not be updated.") from exc


def create_volume(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    work_id: uuid.UUID,
    values: Mapping[str, object],
) -> Volume:
    workspace = _authorized_workspace(actor, workspace_id)
    return cast(
        Volume,
        _create_structure_record(
            workspace=workspace,
            work_id=work_id,
            model=Volume,
            values=values,
            label="Volume",
        ),
    )


def update_volume(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    work_id: uuid.UUID,
    volume_id: uuid.UUID,
    values: Mapping[str, object],
) -> Volume:
    workspace = _authorized_workspace(actor, workspace_id)
    return cast(
        Volume,
        _update_structure_record(
            workspace=workspace,
            work_id=work_id,
            record_id=volume_id,
            model=Volume,
            values=values,
            label="Volume",
        ),
    )


def create_arc(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    work_id: uuid.UUID,
    values: Mapping[str, object],
) -> Arc:
    workspace = _authorized_workspace(actor, workspace_id)
    return cast(
        Arc,
        _create_structure_record(
            workspace=workspace,
            work_id=work_id,
            model=Arc,
            values=values,
            label="Arc",
        ),
    )


def update_arc(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    work_id: uuid.UUID,
    arc_id: uuid.UUID,
    values: Mapping[str, object],
) -> Arc:
    workspace = _authorized_workspace(actor, workspace_id)
    return cast(
        Arc,
        _update_structure_record(
            workspace=workspace,
            work_id=work_id,
            record_id=arc_id,
            model=Arc,
            values=values,
            label="Arc",
        ),
    )


def create_chapter(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    work_id: uuid.UUID,
    values: Mapping[str, object],
) -> Chapter:
    workspace = _authorized_workspace(actor, workspace_id)
    return cast(
        Chapter,
        _create_structure_record(
            workspace=workspace,
            work_id=work_id,
            model=Chapter,
            values=values,
            label="Chapter",
        ),
    )


def update_chapter(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    work_id: uuid.UUID,
    chapter_id: uuid.UUID,
    values: Mapping[str, object],
) -> Chapter:
    workspace = _authorized_workspace(actor, workspace_id)
    return cast(
        Chapter,
        _update_structure_record(
            workspace=workspace,
            work_id=work_id,
            record_id=chapter_id,
            model=Chapter,
            values=values,
            label="Chapter",
        ),
    )


def update_scene_placement(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    scene_id: uuid.UUID,
    values: Mapping[str, object],
) -> Scene:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            scene = Scene.objects.select_for_update().get(id=scene_id, workspace=workspace)
            if scene.lifecycle != Scene.Lifecycle.ACTIVE:
                raise LifecycleDisallowsMutation("Archived Scene placement is read-only.")
            previous_work_id = scene.work_id
            _apply_scene_placement(scene, workspace, values)
            scene.version += 1
            scene.full_clean()
            scene.save(
                update_fields=(
                    "work",
                    "volume",
                    "arc",
                    "chapter",
                    "structure_order",
                    "version",
                    "updated_at",
                )
            )
            _touch_works(workspace, (previous_work_id, scene.work_id))
            if scene.chapter_id:
                Chapter.objects.filter(id=scene.chapter_id, workspace=workspace).update(
                    updated_at=timezone.now()
                )
            return scene
    except Scene.DoesNotExist as exc:
        raise StoryStructureInaccessible("Scene is unavailable.") from exc
    except LifecycleDisallowsMutation:
        raise
    except (IntegrityError, ValidationError) as exc:
        raise StoryStructureConflict("Scene placement could not be updated.") from exc


def create_scene_in_chapter(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    work_id: uuid.UUID,
    chapter_id: uuid.UUID,
    title: str,
) -> SceneMutationResult:
    workspace = _authorized_workspace(actor, workspace_id)
    try:
        with transaction.atomic():
            chapter = Chapter.objects.select_for_update().get(
                id=chapter_id, workspace=workspace, work_id=work_id
            )
            result = create_scene(actor=actor, workspace_id=workspace.id, title=title)
            update_scene_placement(
                actor=actor,
                workspace_id=workspace.id,
                scene_id=result.scene.id,
                values={
                    "work": chapter.work,
                    "volume": chapter.volume,
                    "arc": chapter.arc,
                    "chapter": chapter,
                    "structure_order": None,
                },
            )
            result.scene.refresh_from_db()
            return result
    except Chapter.DoesNotExist as exc:
        raise StoryStructureInaccessible("Chapter is unavailable.") from exc


def delete_structure_record(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    work_id: uuid.UUID,
    record_kind: str,
    record_id: uuid.UUID,
) -> None:
    workspace = _authorized_workspace(actor, workspace_id)
    models_by_kind: dict[str, type[Work | Volume | Arc | Chapter]] = {
        "work": Work,
        "volume": Volume,
        "arc": Arc,
        "chapter": Chapter,
    }
    model = models_by_kind.get(record_kind)
    if model is None:
        raise StoryStructureConflict("Unsupported structure record.")
    filters: dict[str, object] = {"id": record_id, "workspace": workspace}
    if model is not Work:
        filters["work_id"] = work_id
    try:
        with transaction.atomic():
            record = model.objects.select_for_update().get(**filters)
            record.delete()
            if model is not Work:
                _touch_work(work_id, workspace)
    except model.DoesNotExist as exc:
        raise StoryStructureInaccessible("Structure record is unavailable.") from exc
    except ProtectedError as exc:
        raise StoryStructureConflict(
            "Reassign or remove contained structure before deletion."
        ) from exc


def _create_structure_record(
    *,
    workspace: Workspace,
    work_id: uuid.UUID,
    model: type[Volume | Arc | Chapter],
    values: Mapping[str, object],
    label: str,
) -> Volume | Arc | Chapter:
    record_values = dict(values)
    try:
        with transaction.atomic():
            work = Work.objects.select_for_update().get(id=work_id, workspace=workspace)
            if record_values.get("order") is None:
                highest = model.objects.filter(work=work).aggregate(value=models.Max("order"))[
                    "value"
                ]
                record_values["order"] = ORDER_STEP if highest is None else highest + ORDER_STEP
            record = model(work=work, workspace=workspace, **record_values)
            record.full_clean()
            record.save()
            _touch_work(work.id, workspace)
            return record
    except Work.DoesNotExist as exc:
        raise StoryStructureInaccessible("Work is unavailable.") from exc
    except (IntegrityError, ValidationError) as exc:
        raise StoryStructureConflict(f"{label} could not be created.") from exc


def _update_structure_record(
    *,
    workspace: Workspace,
    work_id: uuid.UUID,
    record_id: uuid.UUID,
    model: type[Volume | Arc | Chapter],
    values: Mapping[str, object],
    label: str,
) -> Volume | Arc | Chapter:
    try:
        with transaction.atomic():
            record = model.objects.select_for_update().get(
                id=record_id, workspace=workspace, work_id=work_id
            )
            _apply_values(record, values)
            record.full_clean()
            record.save()
            _touch_work(work_id, workspace)
            return record
    except model.DoesNotExist as exc:
        raise StoryStructureInaccessible(f"{label} is unavailable.") from exc
    except (IntegrityError, ValidationError) as exc:
        raise StoryStructureConflict(f"{label} could not be updated.") from exc


def _apply_scene_placement(
    scene: Scene,
    workspace: Workspace,
    values: Mapping[str, object],
) -> None:
    work = values.get("work")
    if work is None:
        scene.work = None
        scene.volume = None
        scene.arc = None
        scene.chapter = None
        scene.structure_order = None
        return
    if not isinstance(work, Work) or work.workspace_id != workspace.id:
        raise ValidationError("Scene Work is invalid.")
    volume = values.get("volume")
    arc = values.get("arc")
    chapter = values.get("chapter")
    order = values.get("structure_order")
    scene.work = work
    scene.volume = volume if isinstance(volume, Volume) else None
    scene.arc = arc if isinstance(arc, Arc) else None
    scene.chapter = chapter if isinstance(chapter, Chapter) else None
    if order is None:
        siblings = Scene.objects.filter(
            workspace=workspace,
            work=work,
            volume=scene.volume,
            arc=scene.arc,
            chapter=scene.chapter,
        ).exclude(id=scene.id)
        highest = siblings.aggregate(value=models.Max("structure_order"))["value"]
        scene.structure_order = ORDER_STEP if highest is None else highest + ORDER_STEP
    else:
        scene.structure_order = cast(int, order)


def _apply_values(record: object, values: Mapping[str, object]) -> None:
    for field, value in values.items():
        setattr(record, field, value)


def _touch_work(work_id: uuid.UUID, workspace: Workspace) -> None:
    Work.objects.filter(id=work_id, workspace=workspace).update(updated_at=timezone.now())


def _touch_works(workspace: Workspace, work_ids: tuple[uuid.UUID | None, ...]) -> None:
    Work.objects.filter(
        workspace=workspace, id__in={value for value in work_ids if value is not None}
    ).update(updated_at=timezone.now())


def _authorized_workspace(actor: Account | AnonymousUser, workspace_id: uuid.UUID) -> Workspace:
    return get_authorized_workspace(actor, workspace_id)
