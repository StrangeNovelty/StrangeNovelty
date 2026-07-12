import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils import timezone

from accounts.models import Account
from jobs.exceptions import TerminalJobError
from jobs.models import Job
from jobs.services import enqueue_job
from legacy_imports.models import (
    IdentityMapping,
    ImportBatch,
    ImportFinding,
    ImportProvenance,
    StagedRevision,
    StagedScene,
)
from legacy_imports.parser import TRANSFORMATION_VERSION, LegacyImportError, read_legacy_artifact
from scenes.content import CONTENT_FORMAT_VERSION, NORMALIZATION_VERSION, content_sha256
from scenes.models import MutationOperation, Scene, SceneRevision
from scenes.search_indexing import invalidate_and_enqueue_scene_search
from workspaces.services import get_authorized_workspace

ORDERING_STEP = 1024


@dataclass(frozen=True, slots=True)
class StageResult:
    batch: ImportBatch
    replayed: bool


def stage_legacy_import(
    *, account: Account | AnonymousUser, workspace_id: uuid.UUID, source_path: Path
) -> StageResult:
    workspace = get_authorized_workspace(account, workspace_id)
    artifact = read_legacy_artifact(source_path)
    if not isinstance(account, Account):
        raise Http404("Workspace is unavailable.")
    existing = ImportBatch.objects.filter(
        workspace=workspace,
        source_fingerprint=artifact.fingerprint,
        transformation_version=TRANSFORMATION_VERSION,
    ).first()
    if existing is not None:
        return StageResult(existing, True)
    try:
        with transaction.atomic():
            batch = ImportBatch.objects.create(
                workspace=workspace,
                source_fingerprint=artifact.fingerprint,
                source_size=artifact.size,
                requested_by=account,
                state=ImportBatch.State.VALIDATING,
            )
            _stage_records(batch, artifact.scenes)
            staging_fingerprint = _staging_fingerprint(batch)
            fingerprint = hashlib.sha256(
                json.dumps(
                    {
                        "batch": str(batch.id),
                        "source": artifact.fingerprint,
                        "transformation": TRANSFORMATION_VERSION,
                        "workspace": str(workspace.id),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            enqueue = enqueue_job(
                workspace=workspace,
                caller="operator",
                caller_reference=f"account-{account.id.hex}",
                idempotency_key=f"legacy-import-{batch.id.hex}",
                request_fingerprint=fingerprint,
                job_type="validate_legacy_import",
                target_category="import_batch",
                target_id=batch.id,
                projection_version=TRANSFORMATION_VERSION,
            )
            ImportBatch.objects.filter(id=batch.id).update(
                state=ImportBatch.State.AWAITING_APPROVAL,
                staging_job=enqueue.job,
                staging_fingerprint=staging_fingerprint,
                validated_at=timezone.now(),
            )
            batch.refresh_from_db()
            return StageResult(batch, False)
    except IntegrityError as exc:
        raise LegacyImportError("Import staging conflicted with existing records.") from exc


def _stage_records(batch: ImportBatch, parsed_scenes: tuple) -> None:
    used_ordering = set(
        Scene.objects.filter(workspace=batch.workspace).values_list("ordering", flat=True)
    )
    transformed = warnings = 0
    for index, item in enumerate(parsed_scenes, start=1):
        proposed_ordering = item.ordering if item.ordering is not None else index * ORDERING_STEP
        while proposed_ordering in used_ordering:
            warnings += 1
            ImportFinding.objects.create(
                batch=batch,
                source_entity_type="scene",
                source_identifier=item.source_id,
                issue_code="ordering_collision",
                severity=ImportFinding.Severity.WARNING,
                field_category="ordering",
            )
            proposed_ordering += ORDERING_STEP
        used_ordering.add(proposed_ordering)
        duplicate = Scene.objects.filter(workspace=batch.workspace, title=item.title).exists()
        current_source = next(
            revision
            for revision in item.revisions
            if revision.source_id == item.current_revision_id
        )
        content_duplicate = Scene.objects.filter(
            workspace=batch.workspace,
            current_revision__content_sha256=current_source.target_content_hash,
        ).exists()
        status = (
            StagedScene.Status.WARNING
            if duplicate or content_duplicate or item.unsupported_fields
            else StagedScene.Status.ACCEPTED
        )
        staged_scene = StagedScene.objects.create(
            batch=batch,
            source_identifier=item.source_id,
            proposed_title=item.title,
            proposed_lifecycle=item.lifecycle,
            proposed_ordering=proposed_ordering,
            current_source_revision=item.current_revision_id,
            source_fingerprint=hashlib.sha256(item.source_id.encode()).hexdigest(),
            status=status,
        )
        IdentityMapping.objects.create(
            batch=batch,
            source_entity_type=IdentityMapping.EntityType.SCENE,
            source_identifier=item.source_id,
            target_entity_type=IdentityMapping.EntityType.SCENE,
            target_uuid=staged_scene.proposed_scene_id,
        )
        if duplicate:
            warnings += 1
            ImportFinding.objects.create(
                batch=batch,
                source_entity_type="scene",
                source_identifier=item.source_id,
                issue_code="title_duplicate_candidate",
                severity=ImportFinding.Severity.DUPLICATE,
                field_category="title",
            )
        if content_duplicate:
            warnings += 1
            ImportFinding.objects.create(
                batch=batch,
                source_entity_type="scene",
                source_identifier=item.source_id,
                issue_code="content_duplicate_candidate",
                severity=ImportFinding.Severity.DUPLICATE,
                field_category="content_hash",
            )
        for field in item.unsupported_fields:
            warnings += 1
            ImportFinding.objects.create(
                batch=batch,
                source_entity_type="scene",
                source_identifier=item.source_id,
                issue_code="unsupported_scene_field",
                severity=ImportFinding.Severity.UNSUPPORTED,
                field_category=field[:32],
            )
        for number, revision in enumerate(item.revisions, start=1):
            if revision.transformed:
                transformed += 1
                ImportFinding.objects.create(
                    batch=batch,
                    source_entity_type="revision",
                    source_identifier=revision.source_id,
                    issue_code="content_normalized",
                    severity=ImportFinding.Severity.TRANSFORMED,
                    field_category="content",
                )
            staged_revision = StagedRevision.objects.create(
                batch=batch,
                staged_scene=staged_scene,
                source_identifier=revision.source_id,
                proposed_revision_number=number,
                content=revision.content,
                source_content_hash=revision.source_content_hash,
                target_content_hash=revision.target_content_hash,
                source_timestamp=revision.timestamp,
                chronology=(
                    StagedRevision.Chronology.TRUSTED
                    if revision.timestamp is not None
                    else StagedRevision.Chronology.UNCERTAIN
                ),
                is_current=revision.source_id == item.current_revision_id,
            )
            IdentityMapping.objects.create(
                batch=batch,
                source_entity_type=IdentityMapping.EntityType.REVISION,
                source_identifier=f"{item.source_id}:{revision.source_id}",
                target_entity_type=IdentityMapping.EntityType.REVISION,
                target_uuid=staged_revision.proposed_revision_id,
            )
    ImportBatch.objects.filter(id=batch.id).update(
        accepted_count=len(parsed_scenes),
        transformed_count=transformed,
        warning_count=warnings,
    )


def validate_staged_import_job(job_id: str) -> None:
    job = Job.execution_objects.get(id=uuid.UUID(job_id))
    batch = ImportBatch.objects.get(id=job.target_id, workspace_id=job.workspace_id)
    if job.projection_version != TRANSFORMATION_VERSION:
        raise LegacyImportError("Import transformation version is obsolete.")
    if batch.state not in (ImportBatch.State.AWAITING_APPROVAL, ImportBatch.State.APPROVED):
        return
    try:
        _validate_staging(batch)
    except LegacyImportError as exc:
        ImportBatch.objects.filter(id=batch.id).update(
            state=ImportBatch.State.VALIDATION_FAILED,
            failure_classification=ImportBatch.Failure.INTEGRITY,
            failed_at=timezone.now(),
        )
        raise TerminalJobError("Legacy import staging validation failed.") from exc


def _validate_staging(batch: ImportBatch) -> None:
    for scene in batch.staged_scenes.all():
        revisions = scene.staged_revisions.all()
        if revisions.count() < 1 or revisions.filter(is_current=True).count() != 1:
            raise LegacyImportError("Staging integrity validation failed.")
        if any(content_sha256(item.content) != item.target_content_hash for item in revisions):
            raise LegacyImportError("Staged content integrity validation failed.")
    if batch.staging_fingerprint != _staging_fingerprint(batch):
        raise LegacyImportError("Staging integrity fingerprint changed.")


def _staging_fingerprint(batch: ImportBatch) -> str:
    values: list[dict[str, object]] = []
    for scene in batch.staged_scenes.order_by("proposed_ordering", "id"):
        values.append(
            {
                "current": scene.current_source_revision,
                "id": str(scene.proposed_scene_id),
                "lifecycle": scene.proposed_lifecycle,
                "ordering": scene.proposed_ordering,
                "source": scene.source_identifier,
                "title": scene.proposed_title,
                "revisions": [
                    {
                        "current": revision.is_current,
                        "hash": content_sha256(revision.content),
                        "id": str(revision.proposed_revision_id),
                        "number": revision.proposed_revision_number,
                        "source": revision.source_identifier,
                    }
                    for revision in scene.staged_revisions.order_by(
                        "proposed_revision_number", "id"
                    )
                ],
            }
        )
    return hashlib.sha256(
        json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def approve_import(*, account: Account, batch_id: uuid.UUID) -> ImportBatch:
    with transaction.atomic():
        batch = cast(ImportBatch, ImportBatch.objects.select_for_update().get(id=batch_id))
        get_authorized_workspace(account, batch.workspace_id)
        if batch.state == ImportBatch.State.APPROVED and batch.approved_by_id == account.id:
            return batch
        if batch.state != ImportBatch.State.AWAITING_APPROVAL:
            raise LegacyImportError("Import Batch is not awaiting approval.")
        _validate_staging(batch)
        ImportBatch.objects.filter(id=batch.id).update(
            state=ImportBatch.State.APPROVED,
            approved_by=account,
            approved_at=timezone.now(),
            approved_staging_fingerprint=batch.staging_fingerprint,
        )
        return cast(ImportBatch, ImportBatch.objects.get(id=batch.id))


def apply_import(
    *,
    account: Account,
    batch_id: uuid.UUID,
    source_path: Path,
    acknowledge_nonempty: bool,
) -> ImportBatch:
    preliminary = cast(ImportBatch, ImportBatch.objects.only("workspace_id").get(id=batch_id))
    get_authorized_workspace(account, preliminary.workspace_id)
    artifact = read_legacy_artifact(source_path)
    with transaction.atomic():
        batch = cast(
            ImportBatch,
            ImportBatch.objects.select_for_update().select_related("workspace").get(id=batch_id),
        )
        workspace = get_authorized_workspace(account, batch.workspace_id)
        if batch.state == ImportBatch.State.APPLIED:
            return batch
        if batch.state != ImportBatch.State.APPROVED or batch.approved_by_id is None:
            raise LegacyImportError("Import Batch is not approved.")
        if artifact.fingerprint != batch.source_fingerprint or artifact.size != batch.source_size:
            raise LegacyImportError("Source artifact integrity changed after staging.")
        if batch.approved_staging_fingerprint != batch.staging_fingerprint:
            raise LegacyImportError("Approved staging fingerprint changed.")
        if Scene.objects.filter(workspace=workspace).exists() and not acknowledge_nonempty:
            raise LegacyImportError("Non-empty target Workspace acknowledgement is required.")
        _validate_staging(batch)
        ImportBatch.objects.filter(id=batch.id).update(state=ImportBatch.State.APPLYING)
        for staged in batch.staged_scenes.select_for_update().order_by("proposed_ordering", "id"):
            _apply_scene(batch, staged, account)
        ImportBatch.objects.filter(id=batch.id).update(
            state=ImportBatch.State.APPLIED, applied_at=timezone.now()
        )
        return cast(ImportBatch, ImportBatch.objects.get(id=batch.id))


def _apply_scene(batch: ImportBatch, staged: StagedScene, account: Account) -> None:
    if Scene.objects.filter(id=staged.proposed_scene_id).exists():
        raise LegacyImportError("Proposed target identity already exists.")
    scene = Scene.objects.create(
        id=staged.proposed_scene_id,
        workspace=batch.workspace,
        title=staged.proposed_title,
        lifecycle=staged.proposed_lifecycle,
        ordering=staged.proposed_ordering,
        version=0,
        current_revision=None,
    )
    staged_mapping = IdentityMapping.objects.get(
        batch=batch,
        source_entity_type=IdentityMapping.EntityType.SCENE,
        target_uuid=scene.id,
    )
    scene_operation = MutationOperation.objects.create(
        workspace=batch.workspace,
        operation_type=MutationOperation.OperationType.SCENE_IMPORTED,
        source=MutationOperation.Source.IMPORT,
        actor=account,
        scene=scene,
    )
    ImportProvenance.objects.create(
        batch=batch,
        mapping=staged_mapping,
        mutation_operation=scene_operation,
        transformation_version=TRANSFORMATION_VERSION,
    )
    IdentityMapping.objects.filter(id=staged_mapping.id).update(state=IdentityMapping.State.APPLIED)
    previous = None
    current = None
    revisions = list(staged.staged_revisions.order_by("proposed_revision_number", "id"))
    for staged_revision in revisions:
        operation = MutationOperation.objects.create(
            workspace=batch.workspace,
            operation_type=MutationOperation.OperationType.SCENE_REVISION_IMPORTED,
            source=MutationOperation.Source.IMPORT,
            actor=account,
            scene=scene,
        )
        revision = SceneRevision.objects.create(
            id=staged_revision.proposed_revision_id,
            workspace=batch.workspace,
            scene=scene,
            content=staged_revision.content,
            content_sha256=staged_revision.target_content_hash,
            revision_number=staged_revision.proposed_revision_number,
            content_format_version=CONTENT_FORMAT_VERSION,
            normalization_version=NORMALIZATION_VERSION,
            base_revision=previous,
            source=SceneRevision.Source.IMPORT,
            actor=account,
            mutation_operation=operation,
        )
        mapping = IdentityMapping.objects.get(
            batch=batch,
            source_entity_type=IdentityMapping.EntityType.REVISION,
            target_uuid=revision.id,
        )
        ImportProvenance.objects.create(
            batch=batch,
            mapping=mapping,
            mutation_operation=operation,
            transformation_version=TRANSFORMATION_VERSION,
        )
        IdentityMapping.objects.filter(id=mapping.id).update(state=IdentityMapping.State.APPLIED)
        previous = revision
        if staged_revision.is_current:
            current = revision
    if current is None:
        raise LegacyImportError("Staged Scene has no current Revision.")
    Scene.objects.filter(id=scene.id).update(current_revision=current, version=len(revisions))
    StagedScene.objects.filter(id=staged.id).update(status=StagedScene.Status.APPLIED)
    scene.refresh_from_db()
    invalidate_and_enqueue_scene_search(scene, current)


def cancel_import(*, account: Account, batch_id: uuid.UUID) -> ImportBatch:
    with transaction.atomic():
        batch = cast(ImportBatch, ImportBatch.objects.select_for_update().get(id=batch_id))
        get_authorized_workspace(account, batch.workspace_id)
        if batch.state in (ImportBatch.State.APPLIED, ImportBatch.State.APPLYING):
            raise LegacyImportError("Applied or applying imports cannot be cancelled.")
        ImportBatch.objects.filter(id=batch.id).update(
            state=ImportBatch.State.CANCELLED, cancelled_at=timezone.now()
        )
        return cast(ImportBatch, ImportBatch.objects.get(id=batch.id))


def quarantine_unfinished_imports() -> int:
    unfinished = (
        ImportBatch.State.CREATED,
        ImportBatch.State.VALIDATING,
        ImportBatch.State.STAGED,
        ImportBatch.State.AWAITING_APPROVAL,
        ImportBatch.State.APPROVED,
        ImportBatch.State.APPLYING,
    )
    return cast(
        int,
        ImportBatch.objects.filter(state__in=unfinished).update(
            state=ImportBatch.State.QUARANTINED,
            quarantined_at=timezone.now(),
            approved_by=None,
            approved_at=None,
            approved_staging_fingerprint="",
        ),
    )


def discard_staging(*, account: Account, batch_id: uuid.UUID) -> int:
    with transaction.atomic():
        batch = cast(ImportBatch, ImportBatch.objects.select_for_update().get(id=batch_id))
        get_authorized_workspace(account, batch.workspace_id)
        if batch.state == ImportBatch.State.APPLIED:
            raise LegacyImportError("Applied import staging cannot be discarded here.")
        count = batch.staged_revisions.count() + batch.staged_scenes.count()
        batch.findings.all().delete()
        batch.staged_revisions.all().delete()
        batch.staged_scenes.all().delete()
        batch.mappings.all().delete()
        ImportBatch.objects.filter(id=batch.id).update(
            state=ImportBatch.State.CANCELLED, cancelled_at=timezone.now()
        )
        return cast(int, count)
