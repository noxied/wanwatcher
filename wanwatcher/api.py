"""HTTP status API for WANwatcher.

Serves health, status, and Prometheus metrics endpoints from a background
thread using only the standard library. The server is best-effort: a busy
port logs an error but never crashes the application.
"""

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, Optional

from wanwatcher.config import APIConfig
from wanwatcher.metrics import Metrics

logger = logging.getLogger(__name__)

_JSON_CONTENT_TYPE = "application/json; charset=utf-8"
_METRICS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


class _StatusRequestHandler(BaseHTTPRequestHandler):
    """Request handler bound to a StatusServer via the server instance."""

    server: "_StatusHTTPServer"
    server_version = "WANwatcher"

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("%s - %s", self.address_string(), format % args)

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self._send(code, body, _JSON_CONTENT_TYPE)

    def do_GET(self) -> None:  # noqa: N802 - http.server naming convention
        try:
            self._route()
        except Exception:  # pragma: no cover - last-resort guard
            logger.exception("Unhandled error serving %s", self.path)
            try:
                self._send_json(500, {"status": "error"})
            except Exception:
                logger.debug("Could not send 500 response", exc_info=True)

    def _route(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/healthz":
            self._handle_healthz()
        elif path == "/api/status":
            self._handle_status()
        elif path == "/metrics":
            self._handle_metrics()
        elif path == "/":
            self._send_json(
                200,
                {
                    "app": "wanwatcher",
                    "endpoints": ["/healthz", "/api/status", "/metrics"],
                },
            )
        else:
            self._send_json(404, {"error": "not found"})

    def _handle_healthz(self) -> None:
        try:
            status = self.server.status_provider()
        except Exception:
            logger.exception("Status provider failed for /healthz")
            self._send_json(500, {"status": "error"})
            return

        # Liveness: a stuck loop stops refreshing last_check. Once at least one
        # check has run, flag the loop as stale (503) when the gap since the last
        # successful check exceeds a generous multiple of the check interval.
        age = status.get("seconds_since_last_check")
        interval = status.get("check_interval") or 0
        threshold = max(3 * interval, 1800) + 120
        stale = age is not None and age > threshold

        payload = {
            "status": "stale" if stale else "ok",
            "last_check": status.get("last_check"),
            "seconds_since_last_check": age,
            "uptime_seconds": status.get("uptime_seconds"),
        }
        self._send_json(503 if stale else 200, payload)

    def _handle_status(self) -> None:
        try:
            status = self.server.status_provider()
        except Exception:
            logger.exception("Status provider failed for /api/status")
            self._send_json(500, {"status": "error"})
            return
        self._send_json(200, status)

    def _handle_metrics(self) -> None:
        body = self.server.metrics.render().encode("utf-8")
        self._send(200, body, _METRICS_CONTENT_TYPE)

    def _method_not_allowed(self) -> None:
        try:
            self._send_json(405, {"error": "method not allowed"})
        except Exception:
            logger.debug("Could not send 405 response", exc_info=True)

    do_POST = _method_not_allowed
    do_PUT = _method_not_allowed
    do_DELETE = _method_not_allowed
    do_PATCH = _method_not_allowed
    do_HEAD = _method_not_allowed
    do_OPTIONS = _method_not_allowed


class _StatusHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer carrying the status provider and metrics."""

    daemon_threads = True
    # On Windows SO_REUSEADDR lets two sockets bind the same port, hiding
    # "address in use" errors; keep it only on POSIX where it just skips
    # the TIME_WAIT delay on restart.
    allow_reuse_address = os.name != "nt"

    def __init__(
        self,
        server_address: tuple,
        status_provider: Callable[[], Dict[str, Any]],
        metrics: Metrics,
    ) -> None:
        super().__init__(server_address, _StatusRequestHandler)
        self.status_provider = status_provider
        self.metrics = metrics


class StatusServer:
    """Background HTTP server exposing health, status, and metrics."""

    def __init__(
        self,
        config: APIConfig,
        status_provider: Callable[[], Dict[str, Any]],
        metrics: Metrics,
    ) -> None:
        self.config = config
        self.status_provider = status_provider
        self.metrics = metrics
        self._server: Optional[_StatusHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start serving in a daemon thread; log and continue on failure."""
        try:
            self._server = _StatusHTTPServer(
                (self.config.bind, self.config.port),
                self.status_provider,
                self.metrics,
            )
        except OSError as exc:
            logger.error(
                "Could not start status API on %s:%s: %s",
                self.config.bind,
                self.config.port,
                exc,
            )
            self._server = None
            return
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="wanwatcher-status-api",
            daemon=True,
        )
        self._thread.start()
        logger.info("Status API listening on %s:%s", self.config.bind, self.config.port)

    def stop(self) -> None:
        """Shut the server down cleanly; safe to call if start() failed."""
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._server = None
        self._thread = None
        logger.info("Status API stopped")
