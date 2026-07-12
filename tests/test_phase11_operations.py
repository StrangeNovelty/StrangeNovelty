import json
import logging
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.test import Client, override_settings

from operations.logging import PrivacySafeJsonFormatter
from operations.metrics import METRIC_DEFINITIONS, Metric
from operations.readiness import REQUIRED_RUNBOOKS, static_readiness_checks

ROOT = Path(__file__).parents[1]


def test_container_is_non_root_pinned_and_has_distinct_roles() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()
    web = (ROOT / "scripts/start-web.sh").read_text()
    worker = (ROOT / "scripts/start-worker.sh").read_text()
    migration = (ROOT / "scripts/release-migrate.sh").read_text()
    assert "python:3.14.6-slim-bookworm" in dockerfile
    assert "ghcr.io/astral-sh/uv:0.11.28" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "uv sync --frozen" in dockerfile
    assert "gunicorn" in web and "runserver" not in web
    assert "run_worker" in worker and "WORKER_ID is required" in worker
    assert "migrate --noinput" in migration
    assert "migrate" not in web and "migrate" not in worker


def test_dockerignore_excludes_sensitive_and_generated_material() -> None:
    ignored = (ROOT / ".dockerignore").read_text().splitlines()
    for value in (".git", ".env", ".env.*", "private-data", ".venv", "tests"):
        assert value in ignored
    assert "latest" not in (ROOT / "Dockerfile").read_text().casefold()


@override_settings(MAINTENANCE_MODE=False, SERVICE_ROLE="web")
def test_liveness_is_process_only_and_readiness_is_bounded() -> None:
    client = Client()
    live = client.get("/health/live/")
    assert live.status_code == 200 and live.content == b"live"
    assert client.head("/health/live/").status_code == 200
    with patch("operations.health.database_ready", return_value=True):
        ready = client.get("/health/ready/")
        ready_head = client.head("/health/ready/")
    assert ready.status_code == 200 and ready.content == b"ready"
    assert ready_head.status_code == 200
    assert "postgres" not in ready.content.decode().casefold()


@override_settings(MAINTENANCE_MODE=True, SERVICE_ROLE="web")
def test_maintenance_keeps_liveness_blocks_readiness_and_mutations() -> None:
    client = Client()
    assert client.get("/health/live/").status_code == 200
    assert client.get("/health/ready/").status_code == 503
    blocked = client.post("/scenes/new/", {"title": "Synthetic"})
    assert blocked.status_code == 503
    assert b"Maintenance" in blocked.content
    output = StringIO()
    with pytest.raises(CommandError):
        call_command("run_worker", once=True, stdout=output, stderr=output)
    assert "private" not in output.getvalue().casefold()


@override_settings(
    RELEASE_VERSION="v1-test",
    SERVICE_ROLE="web",
)
def test_json_logging_has_only_bounded_operational_fields() -> None:
    record = logging.LogRecord("test", logging.ERROR, "", 0, "private raw message", (), None)
    record.event = "server_error"
    record.correlation_id = "safe-correlation"
    value = json.loads(PrivacySafeJsonFormatter().format(record))
    assert set(value) == {"event", "release", "role", "severity", "timestamp", "correlation_id"}
    assert "private raw message" not in json.dumps(value)


def test_metric_boundary_has_bounded_labels_only() -> None:
    metric = Metric("jobs", (("state", "queued"),), 2)
    assert metric.name == "jobs"
    assert {name for name, _ in metric.labels} <= {"state", "type", "outcome", "role"}
    assert {
        "http_requests",
        "job_queue",
        "job_lease_recovery",
        "authentication_outcome",
        "backup_archive_outcome",
        "restore_readiness_outcome",
        "search_projection_backlog",
        "ai_request_state",
        "import_batch_state",
    } <= set(METRIC_DEFINITIONS)
    source = (ROOT / "src/operations/metrics.py").read_text()
    for forbidden in ("workspace_id", "account_id", "scene_id", "title", "query", "filename"):
        assert forbidden not in source


@override_settings(
    DEBUG=False,
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SECURE_SSL_REDIRECT=True,
    SERVICE_ROLE="web",
    RELEASE_VERSION="v1-test",
    SOURCE_COMMIT="a" * 40,
    BUILD_IDENTIFIER="build-test",
    CONFIGURATION_SCHEMA_VERSION="config-v1",
    AI_ENABLED=False,
    AI_ADAPTER="disabled",
    MAINTENANCE_MODE=False,
    STORAGES={
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}
    },
)
def test_static_readiness_passes_but_private_mfa_gate_fails() -> None:
    checks = static_readiness_checks()
    assert all(checks.values())
    output = StringIO()
    call_command("verify_production_readiness", static_only=True, stdout=output)
    assert "overall=pass" in output.getvalue()
    with pytest.raises(CommandError):
        call_command(
            "verify_production_readiness",
            static_only=True,
            private_content=True,
            stdout=StringIO(),
            stderr=StringIO(),
        )


def test_required_runbooks_exist_and_are_placeholder_only() -> None:
    for relative in REQUIRED_RUNBOOKS:
        path = ROOT / relative
        assert path.is_file()
        content = path.read_text().casefold()
        assert "password=" not in content
        assert "api_key=" not in content
    checklist = (ROOT / "docs/operations/production-readiness-checklist.md").read_text().casefold()
    assert "private-content production approval" in checklist
    assert "prohibited" in checklist


def test_no_cloud_kubernetes_or_external_broker_configuration() -> None:
    names = {path.name for path in ROOT.iterdir()}
    assert not names & {"docker-compose.yml", "compose.yml", "kubernetes", "helm"}
    dockerfile = (ROOT / "Dockerfile").read_text().casefold()
    assert "redis" not in dockerfile and "celery" not in dockerfile
