import json
from pathlib import Path

import pytest

from archives.services import (
    ARCHIVE_FORMAT,
    ARCHIVE_SCHEMA_VERSION,
    MAX_FILE_BYTES,
    PROHIBITED_KEYS,
    ArchiveError,
    _canonical,
    _reject_prohibited_keys,
    verify_restore_readiness,
)


def test_archive_format_is_canonical_utf8_json() -> None:
    first = _canonical({"z": 1, "a": "Unicode ✓"})
    second = _canonical({"a": "Unicode ✓", "z": 1})
    assert first == second
    assert first.endswith(b"\n")
    assert json.loads(first) == {"a": "Unicode ✓", "z": 1}
    assert ARCHIVE_FORMAT == "strange-novelty-workspace"
    assert ARCHIVE_SCHEMA_VERSION == 1


def test_prohibited_authentication_fields_are_rejected() -> None:
    for key in PROHIBITED_KEYS:
        with pytest.raises(ArchiveError, match="prohibited"):
            _reject_prohibited_keys({key: "not-retained"})


def test_archive_limits_are_bounded() -> None:
    assert 0 < MAX_FILE_BYTES <= 10_000_000


def test_readiness_rejects_dry_run_or_incomplete_report(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"validation_passed": True, "dry_run": True}))
    assert not verify_restore_readiness(report)


def test_readiness_accepts_only_complete_non_dry_report(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "validation_passed": True,
                "semantic_verification_passed": True,
                "identity_preserved": True,
                "current_revisions_verified": True,
                "revision_chains_verified": True,
                "scene_versions_verified": True,
                "grants_restored_revoked": True,
                "dry_run": False,
            }
        )
    )
    assert verify_restore_readiness(report, operational_checks_acknowledged=True)


def test_runbook_uses_placeholders_and_separates_artifacts() -> None:
    runbook = (
        Path(__file__).parents[1] / "docs/operations/backup-and-restore-runbook.md"
    ).read_text()
    assert "pg_dump" in runbook and "pg_restore" in runbook
    assert "<database-name>" in runbook
    assert "password=" not in runbook.casefold()
    assert "isolated" in runbook.casefold()
    assert "portable archive is not a postgresql backup" in runbook.casefold()


def test_phase8_adds_no_database_migration() -> None:
    migration_root = Path(__file__).parents[1] / "src/archives"
    assert not (migration_root / "migrations").exists()


def test_no_executable_archive_serialization() -> None:
    service = (Path(__file__).parents[1] / "src/archives/services.py").read_text()
    for forbidden in ("pickle", "yaml", "exec(", "eval(", "RunSQL"):
        assert forbidden not in service
