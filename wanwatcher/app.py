"""WANwatcher application: orchestrates detection, state, notifications,
DDNS, MQTT and the status API in a signal-aware monitoring loop."""

import logging
import random
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from wanwatcher import VERSION
from wanwatcher.config import Config, SecretFileError
from wanwatcher.detector import IPDetector
from wanwatcher.geo import get_geo_data
from wanwatcher.logconfig import configure_logging
from wanwatcher.metrics import Metrics
from wanwatcher.notifiers import build_manager
from wanwatcher.state import State, StateStore
from wanwatcher.updates import check_for_updates

logger = logging.getLogger(__name__)

LEGACY_UPDATE_NOTIFIED_FILE = "/data/update_notified.txt"

# Adaptive backoff after a failed check: start short and grow, capped at the
# normal interval, with jitter so independent instances do not retry in lockstep.
FAILURE_BACKOFF_BASE = 30  # seconds, first retry delay after a failed check
JITTER_MIN = 1.0
JITTER_MAX = 3.0


def setup_logging(log_file: str, log_format: str = "text") -> None:
    configure_logging(log_file, log_format)


class Application:
    def __init__(self, config: Config):
        self.config = config
        self.metrics = Metrics()
        self.detector = IPDetector(
            timeout=config.http_timeout,
            change_confirmation=config.change_confirmation,
        )
        self.store = StateStore(
            config.ip_db_file, legacy_update_file=LEGACY_UPDATE_NOTIFIED_FILE
        )
        self.state: State = State()
        self.notifications = build_manager(config)
        self.shutdown_event = threading.Event()
        self.check_count = 0
        self.consecutive_failures = 0
        self.outage_since: Optional[float] = None
        self.outage_notified = False
        self.last_update_check = time.time()
        self.last_heartbeat = time.time()
        self.last_check_at: Optional[str] = None
        self.geo_data: Optional[Dict[str, Any]] = None

        self.ddns_client = None
        if config.ddns.enabled:
            from wanwatcher.ddns import build_ddns_client

            self.ddns_client = build_ddns_client(
                config.ddns, timeout=config.http_timeout, metrics=self.metrics
            )

        self.api_server = None
        if config.api.enabled:
            from wanwatcher.api import StatusServer

            self.api_server = StatusServer(
                config.api, status_provider=self.status_snapshot, metrics=self.metrics
            )

        self.mqtt = None
        if config.mqtt.enabled:
            from wanwatcher.mqtt import MQTTPublisher

            self.mqtt = MQTTPublisher(config.mqtt, server_name=config.server_name)

    # -- signals -----------------------------------------------------------

    def install_signal_handlers(self) -> None:
        def handler(signum, _frame):
            logger.info(
                "Received signal %s, shutting down...",
                signal.Signals(signum).name,
            )
            self.shutdown_event.set()

        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)

    # -- status for the API ------------------------------------------------

    def status_snapshot(self) -> Dict[str, Any]:
        return {
            "version": VERSION,
            "server_name": self.config.server_name,
            "ipv4": self.state.ipv4,
            "ipv6": self.state.ipv6,
            "geo": self.geo_data,
            "last_check": self.last_check_at,
            "last_change": self.state.last_change,
            "checks_performed": self.check_count,
            "uptime_seconds": round(time.time() - self.metrics.started_at),
            "outage": self.outage_since is not None,
            "history": self.state.history,
            "notifiers": [p.__class__.__name__ for p in self.notifications.providers],
            "ddns_enabled": self.ddns_client is not None,
            "mqtt_enabled": self.mqtt is not None,
        }

    # -- core check --------------------------------------------------------

    def check_ip(self) -> bool:
        self.check_count += 1
        self.metrics.inc("wanwatcher_checks_total")
        try:
            current_ipv4 = (
                self.detector.get_ipv4(previous=self.state.ipv4)
                if self.config.monitor_ipv4
                else None
            )
            current_ipv6 = (
                self.detector.get_ipv6(previous=self.state.ipv6)
                if self.config.monitor_ipv6
                else None
            )

            expected_any = self.config.monitor_ipv4 or self.config.monitor_ipv6
            if expected_any and current_ipv4 is None and current_ipv6 is None:
                self.metrics.inc("wanwatcher_check_failures_total")
                self._handle_check_failure()
                return False

            self._handle_check_success()
            self.last_check_at = datetime.now(timezone.utc).isoformat()
            self.metrics.set_gauge(
                "wanwatcher_last_check_timestamp_seconds", time.time()
            )

            is_first_run = self.state.is_empty()
            old_ipv4, old_ipv6 = self.state.ipv4, self.state.ipv6
            ipv4_changed = self.config.monitor_ipv4 and current_ipv4 != old_ipv4
            ipv6_changed = self.config.monitor_ipv6 and current_ipv6 != old_ipv6

            # A None from the detector while monitoring is enabled means
            # "could not determine", not "address gone"; keep the stored value.
            if self.config.monitor_ipv4 and current_ipv4 is None:
                ipv4_changed = False
                current_ipv4 = old_ipv4
            if self.config.monitor_ipv6 and current_ipv6 is None:
                ipv6_changed = False
                current_ipv6 = old_ipv6

            current_ips = {"ipv4": current_ipv4, "ipv6": current_ipv6}
            previous_ips = {"ipv4": old_ipv4, "ipv6": old_ipv6}

            logger.info("Current IPv4: %s, IPv6: %s", current_ipv4, current_ipv6)

            if is_first_run or ipv4_changed or ipv6_changed:
                if is_first_run:
                    logger.info("First run detected, recording initial addresses")
                else:
                    logger.warning("IP ADDRESS CHANGE DETECTED")
                    if ipv4_changed:
                        logger.warning("  IPv4: %s -> %s", old_ipv4, current_ipv4)
                        self.metrics.inc(
                            "wanwatcher_ip_changes_total", {"family": "ipv4"}
                        )
                    if ipv6_changed:
                        logger.warning("  IPv6: %s -> %s", old_ipv6, current_ipv6)
                        self.metrics.inc(
                            "wanwatcher_ip_changes_total", {"family": "ipv6"}
                        )
                    self.metrics.set_gauge(
                        "wanwatcher_last_change_timestamp_seconds", time.time()
                    )

                self.geo_data = get_geo_data(
                    self.config.ipinfo_token, timeout=self.config.http_timeout
                )

                self.state.ipv4 = current_ipv4
                self.state.ipv6 = current_ipv6
                if not is_first_run:
                    self.store.record_change(self.state, old_ipv4, old_ipv6)
                self.store.save(self.state)

                results = self.notifications.send_to_all(
                    current_ips,
                    previous_ips,
                    self.geo_data,
                    is_first_run,
                    self.config.server_name,
                    VERSION,
                )
                for provider, ok in results.items():
                    self.metrics.inc(
                        "wanwatcher_notifications_total",
                        {"provider": provider, "result": "ok" if ok else "error"},
                    )
            else:
                logger.info("No IP address changes detected")
                # Refresh the state file timestamp so the container healthcheck
                # can tell a live loop from a stuck one.
                self.store.save(self.state)

            if self.ddns_client is not None:
                self.ddns_client.update(current_ipv4, current_ipv6)

            if self.mqtt is not None:
                self.mqtt.publish_state(
                    current_ipv4, current_ipv6, self.geo_data, self.state.last_change
                )

            return True

        except Exception as exc:  # noqa: BLE001 - the loop must survive anything
            logger.error("Error during IP check: %s", exc, exc_info=True)
            self.metrics.inc("wanwatcher_check_failures_total")
            return False

    # -- outage tracking ----------------------------------------------------

    def _handle_check_failure(self) -> None:
        self.consecutive_failures += 1
        logger.error(
            "Failed to retrieve any IP address (%d consecutive failures)",
            self.consecutive_failures,
        )
        events = self.config.events
        if (
            events.outage_detection_enabled
            and self.consecutive_failures == events.outage_threshold
        ):
            self.outage_since = time.time()
            self.outage_notified = True
            logger.warning(
                "Connectivity outage suspected after %d failed checks",
                self.consecutive_failures,
            )
            # Best effort: if only the IP echo services are unreachable the
            # notification still goes out.
            self.notifications.notify_event(
                "Connectivity problem",
                f"No public IP could be determined for "
                f"{self.consecutive_failures} consecutive checks. "
                f"The internet connection may be down.",
                self.config.server_name,
                severity="warning",
            )

    def _handle_check_success(self) -> None:
        if self.outage_since is not None and self.outage_notified:
            duration = time.time() - self.outage_since
            minutes = max(1, round(duration / 60))
            logger.info("Connectivity restored after about %d minute(s)", minutes)
            self.notifications.notify_event(
                "Connectivity restored",
                f"IP detection is working again after roughly "
                f"{minutes} minute(s) without connectivity.",
                self.config.server_name,
                severity="info",
            )
        self.consecutive_failures = 0
        self.outage_since = None
        self.outage_notified = False

    # -- periodic jobs -------------------------------------------------------

    def maybe_check_updates(self) -> None:
        if not self.config.updates.enabled:
            return
        if time.time() - self.last_update_check < self.config.updates.interval:
            return
        self.last_update_check = time.time()
        self._run_update_check()

    def _run_update_check(self) -> None:
        update_info = check_for_updates(
            VERSION,
            already_notified=self.state.update_notified_version,
            timeout=self.config.http_timeout,
        )
        if not update_info:
            return
        results = self.notifications.notify_update(
            update_info, self.config.server_name, VERSION
        )
        if any(results.values()):
            self.state.update_notified_version = update_info["latest_version"]
            try:
                self.store.save(self.state)
            except OSError as exc:
                logger.error("Could not persist update notification state: %s", exc)

    def maybe_heartbeat(self) -> None:
        events = self.config.events
        if not events.heartbeat_enabled:
            return
        if time.time() - self.last_heartbeat < events.heartbeat_interval:
            return
        self.last_heartbeat = time.time()
        parts = []
        if self.state.ipv4:
            parts.append(f"IPv4 {self.state.ipv4}")
        if self.state.ipv6:
            parts.append(f"IPv6 {self.state.ipv6}")
        addresses = ", ".join(parts) if parts else "no address recorded"
        since = self.state.last_change or "startup"
        self.notifications.notify_event(
            "Heartbeat",
            f"WANwatcher is running. Current address: {addresses}. "
            f"Unchanged since {since}.",
            self.config.server_name,
            severity="info",
        )

    # -- scheduling ----------------------------------------------------------

    def _jitter(self) -> float:
        return random.uniform(JITTER_MIN, JITTER_MAX)

    def _next_wait(self) -> float:
        """Seconds to wait before the next check.

        Steady state is the configured interval. After one or more failed
        checks, fall back to a short exponential backoff (capped at the
        interval) plus jitter, so connectivity recovery is noticed sooner and
        many instances do not all retry on the same second.
        """
        if self.consecutive_failures <= 0:
            return float(self.config.check_interval)
        backoff = FAILURE_BACKOFF_BASE * (2 ** (self.consecutive_failures - 1))
        capped = min(self.config.check_interval, backoff)
        return capped + self._jitter()

    # -- lifecycle ------------------------------------------------------------

    def startup_banner(self) -> None:
        cfg = self.config
        logger.info("=" * 60)
        logger.info("WANwatcher v%s started", VERSION)
        logger.info("Server name: %s", cfg.server_name)
        logger.info(
            "Check interval: %d seconds (%d minutes)",
            cfg.check_interval,
            cfg.check_interval // 60,
        )
        logger.info("IPv4 monitoring: %s", "on" if cfg.monitor_ipv4 else "off")
        logger.info("IPv6 monitoring: %s", "on" if cfg.monitor_ipv6 else "off")
        for provider in self.notifications.providers:
            logger.info("Notifier active: %s", provider.__class__.__name__)
        logger.info("DDNS: %s", "on" if self.ddns_client else "off")
        logger.info("Status API: %s", "on" if self.api_server else "off")
        logger.info("MQTT: %s", "on" if self.mqtt else "off")
        logger.info(
            "Geo data: %s",
            "on" if cfg.ipinfo_token else "off (no IPINFO_TOKEN)",
        )
        logger.info("Update check: %s", "on" if cfg.updates.enabled else "off")
        logger.info("=" * 60)

    def run(self) -> int:
        self.install_signal_handlers()
        self.startup_banner()

        if not self.notifications.providers:
            logger.error("FATAL: no notification providers configured")
            logger.error("Enable at least one of Discord, Telegram, Email, Apprise")
            return 1

        if not self.config.monitor_ipv4 and not self.config.monitor_ipv6:
            logger.error("FATAL: both IPv4 and IPv6 monitoring are disabled")
            return 1

        self.state = self.store.load()

        if self.api_server is not None:
            self.api_server.start()
        if self.mqtt is not None:
            self.mqtt.start()

        if self.config.events.notify_on_startup:
            self.notifications.notify_event(
                "Monitoring started",
                f"WANwatcher v{VERSION} is now monitoring this connection.",
                self.config.server_name,
                severity="info",
            )

        if self.config.updates.on_startup and self.config.updates.enabled:
            self._run_update_check()

        logger.info("Performing initial IP check...")
        self.check_ip()

        logger.info(
            "Monitoring continuously (every %d seconds)", self.config.check_interval
        )
        while True:
            wait = self._next_wait()
            if self.consecutive_failures > 0:
                logger.info(
                    "Last check failed; next attempt in %.0fs (adaptive backoff)",
                    wait,
                )
            if self.shutdown_event.wait(timeout=wait):
                break
            try:
                logger.info("Performing check #%d...", self.check_count + 1)
                self.check_ip()
                self.maybe_check_updates()
                self.maybe_heartbeat()
            except Exception as exc:  # noqa: BLE001
                logger.error("Unexpected error in main loop: %s", exc, exc_info=True)
                # Brief, interruptible pause before the next round
                self.shutdown_event.wait(timeout=60)

        self.shutdown()
        return 0

    def shutdown(self) -> None:
        logger.info("Stopping WANwatcher...")
        self.metrics.set_gauge("wanwatcher_up", 0)
        if self.mqtt is not None:
            self.mqtt.stop()
        if self.api_server is not None:
            self.api_server.stop()
        logger.info("Shutdown complete")


def main() -> None:
    try:
        config = Config.from_env()
    except SecretFileError as exc:
        # Logging is not configured yet (its path comes from the config we just
        # failed to load), so report to stderr and fail fast with exit 1.
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s - %(message)s")
        logging.error("Configuration error: %s", exc)
        sys.exit(1)

    setup_logging(config.log_file, config.log_format)

    logger.info("Validating configuration...")
    from wanwatcher.validation import validate_config

    if not validate_config(config):
        logger.error("Configuration validation failed - exiting")
        sys.exit(1)
    logger.info("Configuration validation passed")

    app = Application(config)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
