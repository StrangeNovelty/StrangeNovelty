import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from django.utils.dateparse import parse_datetime

from scenes.content import MAX_CONTENT_CHARACTERS, content_sha256, normalize_scene_content

FORMAT_NAME = "story-engine-scene-export"
SCHEMA_VERSION = 1
TRANSFORMATION_VERSION = "story-engine-scenes-v1"
MAX_SOURCE_BYTES = 25_000_000
MAX_SCENES = 2_000
MAX_REVISIONS = 20_000
SOURCE_ID = re.compile(r"^[A-Za-z0-9._~-]{1,128}$")
SCENE_FIELDS = {"id", "title", "lifecycle", "ordering", "current_revision_id", "revisions"}
REVISION_FIELDS = {"id", "sequence", "content", "created_at"}


class LegacyImportError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ParsedRevision:
    source_id: str
    sequence: int
    source_content_hash: str
    content: str
    target_content_hash: str
    timestamp: datetime | None
    transformed: bool


@dataclass(frozen=True, slots=True)
class ParsedScene:
    source_id: str
    title: str
    lifecycle: str
    ordering: int | None
    current_revision_id: str
    revisions: tuple[ParsedRevision, ...]
    unsupported_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ParsedArtifact:
    fingerprint: str
    size: int
    scenes: tuple[ParsedScene, ...]


def read_legacy_artifact(path: Path) -> ParsedArtifact:
    path = path.expanduser()
    if path.is_symlink() or not path.is_file():
        raise LegacyImportError("Source artifact must be a regular non-symlink file.")
    stat = path.stat()
    if stat.st_size > MAX_SOURCE_BYTES:
        raise LegacyImportError("Source artifact exceeds the size limit.")
    with path.open("rb") as handle:
        descriptor_stat = os.fstat(handle.fileno())
        if not os.path.samestat(stat, descriptor_stat):
            raise LegacyImportError("Source artifact changed during opening.")
        raw = handle.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES or path.stat().st_size != stat.st_size:
        raise LegacyImportError("Source artifact changed or exceeds the size limit.")
    fingerprint = hashlib.sha256(raw).hexdigest()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LegacyImportError("Source artifact is not valid UTF-8 JSON.") from exc
    scenes = _parse_envelope(value)
    return ParsedArtifact(fingerprint, len(raw), scenes)


def _parse_envelope(value: Any) -> tuple[ParsedScene, ...]:
    if not isinstance(value, dict) or set(value) != {"format", "schema_version", "scenes"}:
        raise LegacyImportError("Source envelope fields are invalid.")
    if value["format"] != FORMAT_NAME or value["schema_version"] != SCHEMA_VERSION:
        raise LegacyImportError("Source format or schema version is unsupported.")
    items = value["scenes"]
    if not isinstance(items, list) or len(items) > MAX_SCENES:
        raise LegacyImportError("Source Scene collection is invalid or excessive.")
    scenes = tuple(_parse_scene(item) for item in items)
    ids = [item.source_id for item in scenes]
    if len(ids) != len(set(ids)):
        raise LegacyImportError("Source contains duplicate Scene identifiers.")
    if sum(len(item.revisions) for item in scenes) > MAX_REVISIONS:
        raise LegacyImportError("Source Revision collection is excessive.")
    return scenes


def _parse_scene(value: Any) -> ParsedScene:
    if not isinstance(value, dict):
        raise LegacyImportError("Source Scene record is malformed.")
    required = {"id", "title", "current_revision_id", "revisions"}
    if not required <= set(value):
        raise LegacyImportError("Source Scene is missing required fields.")
    unknown = tuple(sorted(set(value) - SCENE_FIELDS))
    source_id = _source_id(value["id"])
    title = value["title"]
    if not isinstance(title, str) or title != title.strip() or not title or len(title) > 200:
        raise LegacyImportError("Source Scene title is invalid.")
    lifecycle = value.get("lifecycle", "active")
    if lifecycle not in ("active", "archived", "trashed"):
        raise LegacyImportError("Source lifecycle is unsupported.")
    ordering = value.get("ordering")
    if ordering is not None and (not isinstance(ordering, int) or ordering < 0):
        raise LegacyImportError("Source ordering is invalid.")
    revisions_value = value["revisions"]
    if not isinstance(revisions_value, list) or not revisions_value:
        raise LegacyImportError("Source Scene requires at least one complete Revision.")
    revisions = tuple(_parse_revision(item) for item in revisions_value)
    ids = [item.source_id for item in revisions]
    sequences = [item.sequence for item in revisions]
    if len(ids) != len(set(ids)) or len(sequences) != len(set(sequences)):
        raise LegacyImportError("Source Revision identity or sequence is duplicated.")
    current_id = _source_id(value["current_revision_id"])
    if current_id not in ids:
        raise LegacyImportError("Source current Revision is missing.")
    return ParsedScene(
        source_id,
        title,
        lifecycle,
        ordering,
        current_id,
        tuple(sorted(revisions, key=lambda revision: (revision.sequence, revision.source_id))),
        unknown,
    )


def _parse_revision(value: Any) -> ParsedRevision:
    if not isinstance(value, dict) or not {"id", "sequence", "content"} <= set(value):
        raise LegacyImportError("Source Revision is malformed.")
    if set(value) - REVISION_FIELDS:
        raise LegacyImportError("Source Revision contains unsupported fields.")
    source_id = _source_id(value["id"])
    sequence = value["sequence"]
    content = value["content"]
    if not isinstance(sequence, int) or sequence < 1 or not isinstance(content, str):
        raise LegacyImportError("Source Revision fields are invalid.")
    if "\x00" in content or len(content) > MAX_CONTENT_CHARACTERS:
        raise LegacyImportError("Source Revision content is invalid or excessive.")
    normalized = normalize_scene_content(content)
    timestamp = None
    if value.get("created_at") is not None:
        if not isinstance(value["created_at"], str):
            raise LegacyImportError("Source Revision timestamp is invalid.")
        timestamp = parse_datetime(value["created_at"])
        if timestamp is None or timestamp.tzinfo is None:
            raise LegacyImportError("Source Revision timestamp is invalid.")
    return ParsedRevision(
        source_id,
        sequence,
        hashlib.sha256(content.encode("utf-8")).hexdigest(),
        normalized,
        content_sha256(normalized),
        timestamp,
        normalized != content,
    )


def _source_id(value: Any) -> str:
    result = str(value)
    if isinstance(value, bool) or not SOURCE_ID.fullmatch(result):
        raise LegacyImportError("Source identifier is invalid.")
    return result
