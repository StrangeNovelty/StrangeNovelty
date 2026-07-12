import json
import logging
from datetime import UTC, datetime
from typing import Any

from django.conf import settings


class PrivacySafeJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        value: dict[str, Any] = {
            "event": getattr(record, "event", "application_event"),
            "release": settings.RELEASE_VERSION,
            "role": settings.SERVICE_ROLE,
            "severity": record.levelname.lower(),
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
        }
        correlation_id = getattr(record, "correlation_id", "")
        if correlation_id:
            value["correlation_id"] = correlation_id
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
