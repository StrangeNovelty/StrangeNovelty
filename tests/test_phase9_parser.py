import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from legacy_imports.parser import (
    FORMAT_NAME,
    MAX_SOURCE_BYTES,
    LegacyImportError,
    read_legacy_artifact,
)


def _write(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _envelope() -> dict[str, Any]:
    return {
        "format": FORMAT_NAME,
        "schema_version": 1,
        "scenes": [
            {
                "id": "scene-1",
                "title": "Synthetic Record",
                "lifecycle": "active",
                "ordering": 1024,
                "current_revision_id": "revision-2",
                "revisions": [
                    {"id": "revision-1", "sequence": 10, "content": ""},
                    {"id": "revision-2", "sequence": 20, "content": "\r\n"},
                ],
            }
        ],
    }


def test_parser_accepts_versioned_utf8_and_normalizes(tmp_path: Path) -> None:
    artifact = read_legacy_artifact(_write(tmp_path / "input.json", _envelope()))
    assert artifact.scenes[0].revisions[1].content == "\n"
    assert artifact.scenes[0].current_revision_id == "revision-2"
    assert len(artifact.fingerprint) == 64


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(schema_version=2),
        lambda value: value["scenes"].append(value["scenes"][0].copy()),
        lambda value: value["scenes"][0].update(lifecycle="unknown"),
        lambda value: value["scenes"][0]["revisions"][0].update(content="\x00"),
        lambda value: value["scenes"][0]["revisions"][0].update(unknown=True),
    ],
)
def test_parser_rejects_unsupported_or_malformed_input(
    tmp_path: Path, mutation: Callable[[dict[str, Any]], None]
) -> None:
    value = _envelope()
    mutation(value)
    with pytest.raises(LegacyImportError):
        read_legacy_artifact(_write(tmp_path / "input.json", value))


def test_parser_rejects_invalid_utf8_symlink_and_oversize(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"\xff")
    with pytest.raises(LegacyImportError):
        read_legacy_artifact(invalid)
    target = _write(tmp_path / "target.json", _envelope())
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(LegacyImportError):
        read_legacy_artifact(link)
    large = tmp_path / "large.json"
    large.write_bytes(b" " * (MAX_SOURCE_BYTES + 1))
    with pytest.raises(LegacyImportError):
        read_legacy_artifact(large)


def test_parser_never_interprets_paths_or_urls(tmp_path: Path) -> None:
    value = _envelope()
    value["scenes"][0]["path"] = "../outside"
    artifact = read_legacy_artifact(_write(tmp_path / "input.json", value))
    assert artifact.scenes[0].unsupported_fields == ("path",)
