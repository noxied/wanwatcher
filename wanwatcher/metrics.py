"""In-process metrics shared between the main loop and the HTTP API.

A tiny hand-rolled registry that renders the Prometheus text exposition
format. Counters and gauges only; thread-safe; zero dependencies.
"""

import threading
import time
from typing import Dict, Optional, Tuple


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        self._gauges: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        self._help: Dict[str, Tuple[str, str]] = {}  # name -> (type, help text)
        self.started_at = time.time()
        self._declare("wanwatcher_checks_total", "counter", "IP checks performed")
        self._declare(
            "wanwatcher_check_failures_total",
            "counter",
            "IP checks where no address could be retrieved",
        )
        self._declare(
            "wanwatcher_ip_changes_total", "counter", "Detected IP address changes"
        )
        self._declare(
            "wanwatcher_notifications_total",
            "counter",
            "Notification attempts by provider and result",
        )
        self._declare(
            "wanwatcher_ddns_updates_total",
            "counter",
            "DDNS record updates by result",
        )
        self._declare(
            "wanwatcher_last_change_timestamp_seconds",
            "gauge",
            "Unix timestamp of the last detected IP change",
        )
        self._declare(
            "wanwatcher_last_check_timestamp_seconds",
            "gauge",
            "Unix timestamp of the last completed IP check",
        )
        self._declare("wanwatcher_up", "gauge", "Whether the monitor loop is running")
        self._declare(
            "wanwatcher_start_time_seconds", "gauge", "Unix timestamp of process start"
        )
        self.set_gauge("wanwatcher_start_time_seconds", self.started_at)
        self.set_gauge("wanwatcher_up", 1)

    def _declare(self, name: str, mtype: str, help_text: str) -> None:
        self._help[name] = (mtype, help_text)

    @staticmethod
    def _key(
        name: str, labels: Dict[str, str]
    ) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
        return (name, tuple(sorted(labels.items())))

    def inc(
        self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1
    ) -> None:
        labels = labels or {}
        with self._lock:
            key = self._key(name, labels)
            self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        labels = labels or {}
        with self._lock:
            self._gauges[self._key(name, labels)] = value

    @staticmethod
    def _render_labels(labels: Tuple[Tuple[str, str], ...]) -> str:
        if not labels:
            return ""
        inner = ",".join(f'{k}="{v}"' for k, v in labels)
        return "{" + inner + "}"

    def render(self) -> str:
        """Render all metrics in the Prometheus text format."""
        with self._lock:
            lines = []
            seen_help = set()
            for store in (self._counters, self._gauges):
                for (name, labels), value in sorted(store.items()):
                    if name not in seen_help and name in self._help:
                        mtype, help_text = self._help[name]
                        lines.append(f"# HELP {name} {help_text}")
                        lines.append(f"# TYPE {name} {mtype}")
                        seen_help.add(name)
                    lines.append(f"{name}{self._render_labels(labels)} {value}")
            return "\n".join(lines) + "\n"
