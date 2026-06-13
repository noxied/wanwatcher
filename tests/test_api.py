"""Tests for the HTTP status API."""

import json
import socket
import time
import urllib.error
import urllib.request

import pytest

from wanwatcher.api import StatusServer
from wanwatcher.config import APIConfig
from wanwatcher.metrics import Metrics


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server():
    state = {"value": {"last_check": None, "uptime_seconds": 1, "ipv4": "1.2.3.4"}}
    port = _free_port()
    srv = StatusServer(
        APIConfig(enabled=True, bind="127.0.0.1", port=port),
        status_provider=lambda: state["value"],
        metrics=Metrics(),
    )
    srv.start()
    time.sleep(0.3)
    yield port, state
    srv.stop()


def _get(port, path):
    url = f"http://127.0.0.1:{port}{path}"
    with urllib.request.urlopen(url, timeout=5) as resp:
        return resp.status, resp.headers.get("Content-Type"), resp.read()


def test_healthz(server):
    port, _ = server
    status, ctype, body = _get(port, "/healthz")
    assert status == 200
    assert json.loads(body)["status"] == "ok"


def test_status(server):
    port, _ = server
    status, ctype, body = _get(port, "/api/status")
    assert status == 200
    assert "application/json" in ctype
    assert json.loads(body)["ipv4"] == "1.2.3.4"


def test_metrics(server):
    port, _ = server
    status, ctype, body = _get(port, "/metrics")
    assert status == 200
    assert "text/plain" in ctype
    assert b"wanwatcher_up" in body


def test_root(server):
    port, _ = server
    status, _, body = _get(port, "/")
    assert status == 200
    assert json.loads(body)["app"] == "wanwatcher"


def test_unknown_path_404(server):
    port, _ = server
    with pytest.raises(urllib.error.HTTPError) as exc:
        _get(port, "/nope")
    assert exc.value.code == 404


def test_post_405(server):
    port, _ = server
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/healthz", data=b"", method="POST"
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req, timeout=5)
    assert exc.value.code == 405


def test_provider_error_returns_500():
    port = _free_port()

    def boom():
        raise RuntimeError("provider down")

    srv = StatusServer(
        APIConfig(enabled=True, bind="127.0.0.1", port=port),
        status_provider=boom,
        metrics=Metrics(),
    )
    srv.start()
    time.sleep(0.3)
    try:
        with pytest.raises(urllib.error.HTTPError) as exc:
            _get(port, "/healthz")
        assert exc.value.code == 500
    finally:
        srv.stop()


def test_stop_after_failed_start_is_safe():
    # Bind to a port already in use to force start() failure, then stop().
    port = _free_port()
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    blocker.bind(("127.0.0.1", port))
    blocker.listen(1)
    try:
        srv = StatusServer(
            APIConfig(enabled=True, bind="127.0.0.1", port=port),
            status_provider=lambda: {},
            metrics=Metrics(),
        )
        srv.start()
        srv.stop()  # must not raise
    finally:
        blocker.close()


# -- /healthz staleness -------------------------------------------------------


def _serve(provider):
    port = _free_port()
    srv = StatusServer(
        APIConfig(enabled=True, bind="127.0.0.1", port=port),
        status_provider=provider,
        metrics=Metrics(),
    )
    srv.start()
    time.sleep(0.3)
    return srv, port


def test_healthz_ok_when_fresh():
    srv, port = _serve(
        lambda: {"seconds_since_last_check": 12.0, "check_interval": 900}
    )
    try:
        status, _, body = _get(port, "/healthz")
        assert status == 200
        assert json.loads(body)["status"] == "ok"
    finally:
        srv.stop()


def test_healthz_ok_before_first_check():
    srv, port = _serve(
        lambda: {"seconds_since_last_check": None, "check_interval": 900}
    )
    try:
        status, _, _ = _get(port, "/healthz")
        assert status == 200
    finally:
        srv.stop()


def test_healthz_stale_returns_503():
    srv, port = _serve(
        lambda: {"seconds_since_last_check": 999999, "check_interval": 900}
    )
    try:
        with pytest.raises(urllib.error.HTTPError) as exc:
            _get(port, "/healthz")
        assert exc.value.code == 503
        assert json.loads(exc.value.read())["status"] == "stale"
    finally:
        srv.stop()
