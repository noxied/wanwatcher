"""Tests for logging configuration and the JSON formatter."""

import json
import logging

from wanwatcher.logconfig import JSONFormatter, build_formatter, configure_logging


def _record(level=logging.INFO, msg="hello", **kwargs):
    return logging.LogRecord(
        name="wanwatcher.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
        **kwargs,
    )


def test_json_formatter_basic_fields():
    out = JSONFormatter().format(_record(msg="ip changed"))
    data = json.loads(out)
    assert data["level"] == "INFO"
    assert data["logger"] == "wanwatcher.test"
    assert data["message"] == "ip changed"
    assert "timestamp" in data


def test_json_formatter_timestamp_is_utc_iso8601():
    data = json.loads(JSONFormatter().format(_record()))
    # ISO 8601 UTC ends with +00:00 offset
    assert data["timestamp"].endswith("+00:00")


def test_json_formatter_includes_extra_fields():
    rec = _record(msg="changed")
    rec.extra_fields = {"old_ip": "1.1.1.1", "new_ip": "2.2.2.2"}
    data = json.loads(JSONFormatter().format(rec))
    assert data["old_ip"] == "1.1.1.1"
    assert data["new_ip"] == "2.2.2.2"


def test_json_formatter_includes_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        rec = _record(level=logging.ERROR, msg="failed")
        rec.exc_info = sys.exc_info()
        data = json.loads(JSONFormatter().format(rec))
    assert "exception" in data
    assert "ValueError" in data["exception"]


def test_json_formatter_message_with_args():
    rec = logging.LogRecord("x", logging.INFO, __file__, 1, "value=%s", ("42",), None)
    data = json.loads(JSONFormatter().format(rec))
    assert data["message"] == "value=42"


def test_build_formatter_selects_type():
    assert isinstance(build_formatter("json"), JSONFormatter)
    assert isinstance(build_formatter("JSON"), JSONFormatter)
    assert not isinstance(build_formatter("text"), JSONFormatter)
    assert not isinstance(build_formatter("anything-else"), JSONFormatter)


def test_configure_logging_text(tmp_path):
    log_file = tmp_path / "ww.log"
    configure_logging(str(log_file), "text")
    logging.getLogger("wanwatcher.test").info("plain line")
    for h in logging.getLogger().handlers:
        h.flush()
    content = log_file.read_text(encoding="utf-8")
    assert "plain line" in content
    # text format is not JSON
    assert not content.strip().startswith("{")


def test_configure_logging_json(tmp_path):
    log_file = tmp_path / "ww.log"
    configure_logging(str(log_file), "json")
    logging.getLogger("wanwatcher.test").info("json line")
    for h in logging.getLogger().handlers:
        h.flush()
    first = log_file.read_text(encoding="utf-8").strip().splitlines()[0]
    data = json.loads(first)
    assert data["message"] == "json line"


def test_configure_logging_replaces_handlers(tmp_path):
    log_file = tmp_path / "ww.log"
    configure_logging(str(log_file), "text")
    count1 = len(logging.getLogger().handlers)
    configure_logging(str(log_file), "text")
    count2 = len(logging.getLogger().handlers)
    # handlers replaced, not stacked
    assert count1 == count2
