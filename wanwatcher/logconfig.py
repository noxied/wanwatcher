"""Logging configuration: plain text by default, optional structured JSON.

JSON output (``LOG_FORMAT=json``) emits one object per line with a UTC ISO 8601
timestamp, so log aggregators (Loki, Datadog, Splunk) parse the time correctly
without guessing the local zone. No third-party dependency is used.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

TEXT_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


class JSONFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object with a UTC timestamp.

    Extra structured fields can be attached with
    ``logger.info("msg", extra={"extra_fields": {...}})``.
    """

    def format(self, record: logging.LogRecord) -> str:
        data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            data.update(extra)
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def build_formatter(log_format: str) -> logging.Formatter:
    if log_format.strip().lower() == "json":
        return JSONFormatter()
    return logging.Formatter(TEXT_FORMAT)


def configure_logging(log_file: str, log_format: str = "text") -> None:
    """Configure the root logger with file and console handlers.

    Both handlers share the same formatter so text and JSON are consistent
    across the log file and stdout. Safe to call more than once: existing
    handlers are replaced rather than stacked.
    """
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    formatter = build_formatter(log_format)
    handlers: List[logging.Handler] = [
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ]
    for handler in handlers:
        handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for existing in root.handlers[:]:
        root.removeHandler(existing)
    for handler in handlers:
        root.addHandler(handler)
