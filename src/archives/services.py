import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.models import Account
from ai_assistance.services import quarantine_unfinished_ai_requests
from jobs.services import quarantine_unfinished_jobs
from legacy_imports.services import quarantine_unfinished_imports
from scenes.content import CONTENT_FORMAT_VERSION, NORMALIZATION_VERSION
from scenes.models import MutationOperation, Scene, SceneRevision, SceneSearchProjection
from workspaces.models import Workspace, WorkspaceGrant

ARCHIVE_FORMAT = "strange-novelty-workspace"
ARCHIVE_SCHEMA_VERSION = 1
TOOL_VERSION = "phase-8-v1"
MAX_FILES = 16
MAX_FILE_BYTES = 10_000_000
MAX_TOTAL_BYTES = 50_000_000
MAX_RECORDS = 100_000
RECORD_FILES = (
    "records/workspace.json",
    "records/account_references.json",
    "records/grants.json",
    "records/scenes.json",
    "records/mutation_operations.json",
    "records/revisions.json",
)
PROHIBITED_KEYS = {
    "password",
    "password_hash",
    "session_key",
    "csrf",
    "mfa",
    "recovery_code",
    "secret",
    "token",
    "credential",
    "encryption_key",
}


class ArchiveError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ArchiveValidation:
    root: Path
    manifest: dict[str, Any]
    records: dict[str, Any]
    digest: str
    counts: dict[str, int]


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _safe_output(path: Path, *, overwrite: bool) -> Path:
    path = path.expanduser()
    if path.exists() and path.is_symlink():
        raise ArchiveError("Output destination must not be a symlink.")
    if path.exists() and not overwrite:
        raise ArchiveError("Output destination already exists.")
    if any(part == ".." for part in path.parts):
        raise ArchiveError("Output destination is unsafe.")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise ArchiveError("Output parent must not be a symlink.")
    return path


def export_readable_workspace(
    workspace_id: uuid.UUID,
    output: Path,
    *,
    include_trashed: bool = False,
    overwrite: bool = False,
    dry_run: bool = False,
) -> int:
    workspace = Workspace.objects.get(id=workspace_id)
    scene_query = Scene.objects.select_related("current_revision").filter(workspace=workspace)
    if not include_trashed:
        scene_query = scene_query.exclude(lifecycle=Scene.Lifecycle.TRASHED)
    scenes = list(scene_query.order_by("ordering", "id"))
    if dry_run:
        return len(scenes)
    output = _safe_output(output, overwrite=overwrite)
    temporary = Path(tempfile.mkdtemp(prefix="readable-", dir=output.parent))
    try:
        os.chmod(temporary, 0o700)
        scene_dir = temporary / "scenes"
        scene_dir.mkdir(mode=0o700)
        index_lines = ["Strange Novelty readable export", "", f"Scenes: {len(scenes)}", ""]
        for scene in scenes:
            current = scene.current_revision
            if current is None:
                raise ArchiveError("A Scene has no current Revision.")
            filename = f"{scene.ordering:012d}-{scene.id.hex}.txt"
            text = (
                f"Title: {scene.title}\nLifecycle: {scene.lifecycle}\n"
                f"Revision: {current.revision_number}\n\n{current.content}"
            )
            (scene_dir / filename).write_text(text, encoding="utf-8", newline="\n")
            os.chmod(scene_dir / filename, 0o600)
            index_lines.append(f"{filename}\t{scene.lifecycle}")
        (temporary / "index.txt").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
        os.chmod(temporary / "index.txt", 0o600)
        if output.exists():
            shutil.rmtree(output)
        os.replace(temporary, output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return len(scenes)


def export_workspace_archive(
    workspace_id: uuid.UUID,
    output: Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    with transaction.atomic():
        workspace = cast(Workspace, Workspace.objects.select_for_update().get(id=workspace_id))
        snapshot = _snapshot_workspace(workspace)
    counts = {
        name: len(value) if isinstance(value, list) else 1 for name, value in snapshot.items()
    }
    if dry_run:
        return counts
    output = _safe_output(output, overwrite=overwrite)
    temporary = Path(tempfile.mkdtemp(prefix="archive-", dir=output.parent))
    try:
        os.chmod(temporary, 0o700)
        inventory: list[dict[str, Any]] = []
        for relative, key in zip(RECORD_FILES, snapshot, strict=True):
            target = temporary / relative
            target.parent.mkdir(mode=0o700, exist_ok=True)
            data = _canonical(snapshot[key])
            if len(data) > MAX_FILE_BYTES:
                raise ArchiveError("Archive record file exceeds the size limit.")
            target.write_bytes(data)
            os.chmod(target, 0o600)
            inventory.append(
                {"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            )
        digest = hashlib.sha256(_canonical(inventory)).hexdigest()
        manifest = {
            "archive_format": ARCHIVE_FORMAT,
            "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
            "application_compatibility": "version-1",
            "tool_version": TOOL_VERSION,
            "created_at": timezone.now().isoformat(),
            "source_workspace_id": str(workspace.id),
            "source_workspace_name": workspace.name,
            "restore_mode": "same_archive_full_workspace",
            "content_format_version": CONTENT_FORMAT_VERSION,
            "normalization_version": NORMALIZATION_VERSION,
            "record_counts": counts,
            "files": inventory,
            "archive_digest": digest,
            "explicit_exclusions": [
                "passwords_and_authentication_material",
                "sessions",
                "security_events",
                "scene_save_requests",
                "generic_idempotency_records",
                "jobs_and_attempts",
                "search_projections",
                "provider_and_deployment_secrets",
                "legacy_import_staging_findings_and_mappings",
                "ai_requests_suggestions_and_provider_effects",
            ],
        }
        (temporary / "manifest.json").write_bytes(_canonical(manifest))
        os.chmod(temporary / "manifest.json", 0o600)
        validate_workspace_archive(temporary)
        if output.exists():
            shutil.rmtree(output)
        os.replace(temporary, output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return counts


def _snapshot_workspace(workspace: Workspace) -> dict[str, Any]:
    scenes = list(Scene.objects.filter(workspace=workspace).order_by("id"))
    operations = list(MutationOperation.objects.filter(workspace=workspace).order_by("id"))
    revisions = list(
        SceneRevision.objects.filter(workspace=workspace).order_by("scene_id", "revision_number")
    )
    actor_ids = sorted(
        {str(item.actor_id) for item in [*operations, *revisions] if item.actor_id is not None}
        | {str(item.account_id) for item in WorkspaceGrant.objects.filter(workspace=workspace)}
    )
    return {
        "workspace": {
            "id": str(workspace.id),
            "name": workspace.name,
            "is_active": workspace.is_active,
            "created_at": workspace.created_at.isoformat(),
            "updated_at": workspace.updated_at.isoformat(),
        },
        "account_references": [{"id": value} for value in actor_ids],
        "grants": [
            {
                "id": str(item.id),
                "account_id": str(item.account_id),
                "role": item.role,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in WorkspaceGrant.objects.filter(workspace=workspace).order_by("id")
        ],
        "scenes": [
            {
                "id": str(item.id),
                "title": item.title,
                "lifecycle": item.lifecycle,
                "ordering": item.ordering,
                "version": item.version,
                "current_revision_id": str(item.current_revision_id),
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in scenes
        ],
        "mutation_operations": [
            {
                "id": str(item.id),
                "operation_type": item.operation_type,
                "source": item.source,
                "actor_id": str(item.actor_id) if item.actor_id else None,
                "scene_id": str(item.scene_id) if item.scene_id else None,
                "created_at": item.created_at.isoformat(),
            }
            for item in operations
        ],
        "revisions": [
            {
                "id": str(item.id),
                "scene_id": str(item.scene_id),
                "content": item.content,
                "content_sha256": item.content_sha256,
                "revision_number": item.revision_number,
                "content_format_version": item.content_format_version,
                "normalization_version": item.normalization_version,
                "base_revision_id": str(item.base_revision_id) if item.base_revision_id else None,
                "restored_from_id": str(item.restored_from_id) if item.restored_from_id else None,
                "source": item.source,
                "actor_id": str(item.actor_id) if item.actor_id else None,
                "mutation_operation_id": str(item.mutation_operation_id),
                "created_at": item.created_at.isoformat(),
            }
            for item in revisions
        ],
    }


def validate_workspace_archive(root: Path) -> ArchiveValidation:
    root = root.expanduser()
    if not root.is_dir() or root.is_symlink():
        raise ArchiveError("Archive must be a non-symlink directory.")
    paths = list(root.rglob("*"))
    if len(paths) > MAX_FILES or any(path.is_symlink() for path in paths):
        raise ArchiveError("Archive file structure is unsafe or excessive.")
    files = [path for path in paths if path.is_file()]
    total = sum(path.stat().st_size for path in files)
    if total > MAX_TOTAL_BYTES or any(path.stat().st_size > MAX_FILE_BYTES for path in files):
        raise ArchiveError("Archive size exceeds limits.")
    allowed = {"manifest.json", *RECORD_FILES}
    relative = {path.relative_to(root).as_posix() for path in files}
    if relative != allowed:
        raise ArchiveError("Archive file inventory is invalid.")
    manifest = _read_json(root / "manifest.json")
    if (
        manifest.get("archive_format") != ARCHIVE_FORMAT
        or manifest.get("archive_schema_version") != ARCHIVE_SCHEMA_VERSION
        or manifest.get("restore_mode") != "same_archive_full_workspace"
    ):
        raise ArchiveError("Archive version or mode is unsupported.")
    inventory = manifest.get("files")
    if not isinstance(inventory, list) or len(inventory) != len(RECORD_FILES):
        raise ArchiveError("Archive manifest inventory is invalid.")
    expected: dict[str, str] = {}
    for entry in inventory:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "bytes"}:
            raise ArchiveError("Archive file entry is invalid.")
        path = entry["path"]
        if path not in RECORD_FILES or not re.fullmatch(r"records/[a-z_]+\.json", path):
            raise ArchiveError("Archive filename is not allowed.")
        data = (root / path).read_bytes()
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ArchiveError("Archive integrity check failed.")
        expected[path] = entry["sha256"]
    if set(expected) != set(RECORD_FILES):
        raise ArchiveError("Archive record file is missing.")
    digest = hashlib.sha256(_canonical(inventory)).hexdigest()
    if digest != manifest.get("archive_digest"):
        raise ArchiveError("Archive digest does not match.")
    records = {
        key: _read_json(root / path)
        for path, key in zip(
            RECORD_FILES,
            (
                "workspace",
                "account_references",
                "grants",
                "scenes",
                "mutation_operations",
                "revisions",
            ),
            strict=True,
        )
    }
    _reject_prohibited_keys(records)
    counts = manifest.get("record_counts")
    if not isinstance(counts, dict):
        raise ArchiveError("Archive counts are invalid.")
    actual = {key: len(value) if isinstance(value, list) else 1 for key, value in records.items()}
    if actual != counts or sum(actual.values()) > MAX_RECORDS:
        raise ArchiveError("Archive record counts do not match.")
    _validate_relationships(records, manifest)
    return ArchiveValidation(root, manifest, records, digest, actual)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArchiveError("Archive JSON is invalid UTF-8 or malformed.") from exc


def _reject_prohibited_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in PROHIBITED_KEYS:
                raise ArchiveError("Archive contains a prohibited field category.")
            _reject_prohibited_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_prohibited_keys(child)


def _validate_relationships(records: dict[str, Any], manifest: dict[str, Any]) -> None:
    workspace = records["workspace"]
    _require_keys(workspace, {"id", "name", "is_active", "created_at", "updated_at"})
    if not isinstance(workspace["name"], str) or not workspace["name"].strip():
        raise ArchiveError("Workspace record is invalid.")
    _datetime(workspace["created_at"])
    _datetime(workspace["updated_at"])
    for item in records["account_references"]:
        _require_keys(item, {"id"})
    for item in records["grants"]:
        _require_keys(item, {"id", "account_id", "role", "created_at", "updated_at"})
        if item["role"] not in WorkspaceGrant.Role.values:
            raise ArchiveError("Grant role is invalid.")
        _datetime(item["created_at"])
        _datetime(item["updated_at"])
    for item in records["scenes"]:
        _require_keys(
            item,
            {
                "id",
                "title",
                "lifecycle",
                "ordering",
                "version",
                "current_revision_id",
                "created_at",
                "updated_at",
            },
        )
        if (
            not isinstance(item["title"], str)
            or not item["title"].strip()
            or item["lifecycle"] not in Scene.Lifecycle.values
            or not isinstance(item["ordering"], int)
            or not isinstance(item["version"], int)
            or item["version"] < 0
        ):
            raise ArchiveError("Scene record is invalid.")
        _datetime(item["created_at"])
        _datetime(item["updated_at"])
    for item in records["mutation_operations"]:
        _require_keys(
            item,
            {"id", "operation_type", "source", "actor_id", "scene_id", "created_at"},
        )
        if (
            item["operation_type"] not in MutationOperation.OperationType.values
            or item["source"] not in MutationOperation.Source.values
        ):
            raise ArchiveError("Mutation Operation record is invalid.")
        _datetime(item["created_at"])
    for item in records["revisions"]:
        _require_keys(
            item,
            {
                "id",
                "scene_id",
                "content",
                "content_sha256",
                "revision_number",
                "content_format_version",
                "normalization_version",
                "base_revision_id",
                "restored_from_id",
                "source",
                "actor_id",
                "mutation_operation_id",
                "created_at",
            },
        )
        if (
            not isinstance(item["content"], str)
            or item["source"] not in SceneRevision.Source.values
            or not re.fullmatch(r"[0-9a-f]{64}", item["content_sha256"])
            or hashlib.sha256(item["content"].encode("utf-8")).hexdigest() != item["content_sha256"]
        ):
            raise ArchiveError("Revision record is invalid.")
        _datetime(item["created_at"])
    workspace_id = _uuid(workspace.get("id"))
    if str(workspace_id) != manifest.get("source_workspace_id"):
        raise ArchiveError("Workspace identity does not match the manifest.")
    account_ids = {_uuid(item.get("id")) for item in records["account_references"]}
    scene_ids = {_uuid(item.get("id")) for item in records["scenes"]}
    revision_ids = [_uuid(item.get("id")) for item in records["revisions"]]
    operation_ids = {_uuid(item.get("id")) for item in records["mutation_operations"]}
    grant_ids = {_uuid(item.get("id")) for item in records["grants"]}
    if (
        len(account_ids) != len(records["account_references"])
        or len(scene_ids) != len(records["scenes"])
        or len(set(revision_ids)) != len(revision_ids)
        or len(operation_ids) != len(records["mutation_operations"])
        or len(grant_ids) != len(records["grants"])
    ):
        raise ArchiveError("Archive contains duplicate identities.")
    revision_set = set(revision_ids)
    current_ids = {_uuid(item.get("current_revision_id")) for item in records["scenes"]}
    if not current_ids <= revision_set:
        raise ArchiveError("A Scene current Revision is missing.")
    seen_numbers: set[tuple[uuid.UUID, int]] = set()
    revision_scene: dict[uuid.UUID, uuid.UUID] = {}
    for item in records["revisions"]:
        revision_id = _uuid(item.get("id"))
        scene_id = _uuid(item.get("scene_id"))
        if (
            scene_id not in scene_ids
            or _uuid(item.get("mutation_operation_id")) not in operation_ids
        ):
            raise ArchiveError("Revision references are invalid.")
        number = item.get("revision_number")
        if not isinstance(number, int) or number < 1 or (scene_id, number) in seen_numbers:
            raise ArchiveError("Revision numbering is invalid.")
        seen_numbers.add((scene_id, number))
        revision_scene[revision_id] = scene_id
        for key in ("base_revision_id", "restored_from_id"):
            if item.get(key) is not None:
                reference_id = _uuid(item[key])
                if reference_id not in revision_set:
                    raise ArchiveError("Revision lineage is invalid.")
        if item.get("actor_id") is not None and _uuid(item["actor_id"]) not in account_ids:
            raise ArchiveError("Revision actor reference is invalid.")
    for scene in records["scenes"]:
        if revision_scene.get(_uuid(scene["current_revision_id"])) != _uuid(scene["id"]):
            raise ArchiveError("Current Revision belongs to another Scene.")
    for item in records["revisions"]:
        for key in ("base_revision_id", "restored_from_id"):
            if item.get(key) is not None and revision_scene[_uuid(item[key])] != _uuid(
                item["scene_id"]
            ):
                raise ArchiveError("Revision lineage crosses Scenes.")
    for grant in records["grants"]:
        if _uuid(grant.get("account_id")) not in account_ids:
            raise ArchiveError("Grant Account reference is invalid.")
    for operation in records["mutation_operations"]:
        if operation["scene_id"] is not None and _uuid(operation["scene_id"]) not in scene_ids:
            raise ArchiveError("Mutation Operation Scene reference is invalid.")
        if operation["actor_id"] is not None and _uuid(operation["actor_id"]) not in account_ids:
            raise ArchiveError("Mutation Operation actor reference is invalid.")


def _require_keys(value: Any, keys: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise ArchiveError("Archive record shape is invalid.")


def _uuid(value: Any) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ArchiveError("Archive UUID is invalid.") from exc


def _datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ArchiveError("Archive timestamp is invalid.")
    parsed = parse_datetime(value)
    if parsed is None or timezone.is_naive(parsed):
        raise ArchiveError("Archive timestamp is invalid.")
    return cast(datetime, parsed)


def restore_workspace_archive(
    root: Path,
    report_path: Path,
    *,
    dry_run: bool,
    confirmed: bool,
    isolated_acknowledged: bool,
) -> dict[str, Any]:
    validation = validate_workspace_archive(root)
    account_ids = [_uuid(item["id"]) for item in validation.records["account_references"]]
    missing = [value for value in account_ids if not Account.objects.filter(id=value).exists()]
    if missing:
        raise ArchiveError("Required pre-existing Account references are unavailable.")
    if Workspace.objects.exists() or Scene.objects.exists() or SceneRevision.objects.exists():
        raise ArchiveError("Portable restore requires an empty target domain.")
    if dry_run:
        return _verification_report(validation, {}, dry_run=True)
    if not confirmed or not isolated_acknowledged:
        raise ArchiveError("Restore confirmation and isolated-target acknowledgement are required.")
    report_path = _safe_output(report_path, overwrite=False)
    try:
        with transaction.atomic():
            counts = _apply_restore(validation)
            sessions = Session.objects.count()
            Session.objects.all().delete()
            quarantined = quarantine_unfinished_jobs()
            imports_quarantined = quarantine_unfinished_imports()
            ai_requests_quarantined = quarantine_unfinished_ai_requests()
            reset = SceneSearchProjection.objects.count()
            SceneSearchProjection.objects.all().delete()
            report = _verification_report(
                validation,
                counts
                | {
                    "sessions_invalidated": sessions,
                    "jobs_quarantined": quarantined,
                    "imports_quarantined": imports_quarantined,
                    "ai_requests_quarantined": ai_requests_quarantined,
                    "search_projections_reset": reset,
                },
                dry_run=False,
            )
            _atomic_json_file(report_path, report)
    except Exception:
        report_path.unlink(missing_ok=True)
        raise
    return report


def _apply_restore(validation: ArchiveValidation) -> dict[str, int]:
    records = validation.records
    workspace_data = records["workspace"]
    workspace = Workspace.objects.create(
        id=_uuid(workspace_data["id"]),
        name=workspace_data["name"],
        is_active=bool(workspace_data["is_active"]),
    )
    Workspace.objects.filter(id=workspace.id).update(
        created_at=_datetime(workspace_data["created_at"]),
        updated_at=_datetime(workspace_data["updated_at"]),
    )
    now = timezone.now()
    for item in records["grants"]:
        grant = WorkspaceGrant.objects.create(
            id=_uuid(item["id"]),
            workspace=workspace,
            account_id=_uuid(item["account_id"]),
            role=item["role"],
            state=WorkspaceGrant.State.REVOKED,
            revoked_at=now,
        )
        WorkspaceGrant.objects.filter(id=grant.id).update(
            created_at=_datetime(item["created_at"]),
            updated_at=_datetime(item["updated_at"]),
        )
    scenes: dict[uuid.UUID, Scene] = {}
    for item in records["scenes"]:
        scene = Scene.objects.create(
            id=_uuid(item["id"]),
            workspace=workspace,
            title=item["title"],
            lifecycle=item["lifecycle"],
            ordering=item["ordering"],
            version=0,
            current_revision=None,
        )
        Scene.objects.filter(id=scene.id).update(
            created_at=_datetime(item["created_at"]),
            updated_at=_datetime(item["updated_at"]),
        )
        scenes[scene.id] = scene
    operations: dict[uuid.UUID, MutationOperation] = {}
    for item in records["mutation_operations"]:
        operation = MutationOperation.objects.create(
            id=_uuid(item["id"]),
            workspace=workspace,
            operation_type=item["operation_type"],
            source=item["source"],
            actor_id=_uuid(item["actor_id"]) if item["actor_id"] else None,
            scene=scenes.get(_uuid(item["scene_id"])) if item["scene_id"] else None,
        )
        operations[operation.id] = operation
        MutationOperation._base_manager.filter(id=operation.id).update(
            created_at=_datetime(item["created_at"])
        )
    revisions: dict[uuid.UUID, SceneRevision] = {}
    sorted_revisions = sorted(
        records["revisions"], key=lambda item: (item["scene_id"], item["revision_number"])
    )
    for item in sorted_revisions:
        for key in ("base_revision_id", "restored_from_id"):
            if item[key] and _uuid(item[key]) not in revisions:
                raise ArchiveError("Revision lineage is not dependency ordered.")
        revision = SceneRevision.objects.create(
            id=_uuid(item["id"]),
            workspace=workspace,
            scene=scenes[_uuid(item["scene_id"])],
            content=item["content"],
            content_sha256=item["content_sha256"],
            revision_number=item["revision_number"],
            content_format_version=item["content_format_version"],
            normalization_version=item["normalization_version"],
            base_revision=revisions.get(_uuid(item["base_revision_id"]))
            if item["base_revision_id"]
            else None,
            restored_from=revisions.get(_uuid(item["restored_from_id"]))
            if item["restored_from_id"]
            else None,
            source=item["source"],
            actor_id=_uuid(item["actor_id"]) if item["actor_id"] else None,
            mutation_operation=operations[_uuid(item["mutation_operation_id"])],
        )
        revisions[revision.id] = revision
        SceneRevision._base_manager.filter(id=revision.id).update(
            created_at=_datetime(item["created_at"])
        )
    for item in records["scenes"]:
        Scene.objects.filter(id=_uuid(item["id"])).update(
            current_revision_id=_uuid(item["current_revision_id"]),
            version=item["version"],
        )
    _verify_restored_workspace(workspace.id, validation)
    return validation.counts


def _verify_restored_workspace(workspace_id: uuid.UUID, validation: ArchiveValidation) -> None:
    if Workspace.objects.filter(id=workspace_id).count() != 1:
        raise ArchiveError("Restored Workspace identity verification failed.")
    for item in validation.records["scenes"]:
        scene = Scene.objects.get(id=_uuid(item["id"]), workspace_id=workspace_id)
        if (
            scene.current_revision_id != _uuid(item["current_revision_id"])
            or scene.version != item["version"]
        ):
            raise ArchiveError("Restored Scene semantic verification failed.")
    if (
        SceneRevision.objects.filter(workspace_id=workspace_id).count()
        != validation.counts["revisions"]
    ):
        raise ArchiveError("Restored Revision count verification failed.")


def _verification_report(
    validation: ArchiveValidation, actions: dict[str, int], *, dry_run: bool
) -> dict[str, Any]:
    return {
        "report_format": "strange-novelty-restore-verification-v1",
        "tool_version": TOOL_VERSION,
        "verified_at": timezone.now().isoformat(),
        "archive_digest": validation.digest,
        "source_workspace_id": validation.manifest["source_workspace_id"],
        "target_workspace_id": validation.manifest["source_workspace_id"],
        "validation_passed": True,
        "semantic_verification_passed": not dry_run,
        "identity_preserved": not dry_run,
        "current_revisions_verified": not dry_run,
        "revision_chains_verified": True,
        "scene_versions_verified": not dry_run,
        "grants_restored_revoked": not dry_run,
        "sessions_invalidated": actions.get("sessions_invalidated", 0),
        "jobs_quarantined": actions.get("jobs_quarantined", 0),
        "imports_quarantined": actions.get("imports_quarantined", 0),
        "ai_requests_quarantined": actions.get("ai_requests_quarantined", 0),
        "search_projections_reset": actions.get("search_projections_reset", 0),
        "record_counts": validation.counts,
        "dry_run": dry_run,
        "activation_ready": False,
        "warnings": ["Owner authority requires explicit review before activation."],
    }


def verify_restore_readiness(
    report_path: Path, *, operational_checks_acknowledged: bool = False
) -> bool:
    report = _read_json(report_path)
    required = (
        "validation_passed",
        "semantic_verification_passed",
        "identity_preserved",
        "current_revisions_verified",
        "revision_chains_verified",
        "scene_versions_verified",
        "grants_restored_revoked",
    )
    return (
        all(report.get(key) is True for key in required)
        and report.get("dry_run") is False
        and operational_checks_acknowledged
    )


def _atomic_json_file(path: Path, value: Any) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix="report-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical(value))
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
