"""Tests for the Application orchestration logic."""

import os
from unittest.mock import MagicMock

import pytest

from wanwatcher.app import Application
from wanwatcher.config import Config, DiscordConfig, EventsConfig


@pytest.fixture
def config(tmp_path):
    cfg = Config(
        ip_db_file=str(tmp_path / "state.json"),
        log_file=str(tmp_path / "ww.log"),
        monitor_ipv4=True,
        monitor_ipv6=False,
        discord=DiscordConfig(enabled=True, webhook_url="https://discord.com/x"),
    )
    return cfg


@pytest.fixture
def app(config):
    application = Application(config)
    application.detector = MagicMock()
    application.notifications = MagicMock()
    application.notifications.providers = [MagicMock()]
    application.notifications.send_to_all.return_value = {"DiscordNotifier": True}
    application.state = application.store.load()
    return application


def test_first_run_notifies_and_saves(app):
    app.detector.get_ipv4.return_value = "1.2.3.4"
    assert app.check_ip() is True
    app.notifications.send_to_all.assert_called_once()
    assert app.state.ipv4 == "1.2.3.4"
    assert os.path.exists(app.config.ip_db_file)


def test_unchanged_ip_does_not_notify(app):
    app.detector.get_ipv4.return_value = "1.2.3.4"
    app.check_ip()  # first run
    app.notifications.send_to_all.reset_mock()
    app.detector.get_ipv4.return_value = "1.2.3.4"
    mtime_before = os.path.getmtime(app.config.ip_db_file)
    import time

    time.sleep(0.02)
    app.check_ip()
    app.notifications.send_to_all.assert_not_called()
    # State file is still refreshed so the healthcheck sees a live loop.
    assert os.path.getmtime(app.config.ip_db_file) > mtime_before


def test_change_notifies_and_records_history(app):
    app.detector.get_ipv4.return_value = "1.2.3.4"
    app.check_ip()
    app.notifications.send_to_all.reset_mock()
    app.detector.get_ipv4.return_value = "5.6.7.8"
    app.check_ip()
    app.notifications.send_to_all.assert_called_once()
    assert app.state.ipv4 == "5.6.7.8"
    assert len(app.state.history) == 1
    assert app.state.history[0]["old_ipv4"] == "1.2.3.4"
    assert app.state.history[0]["new_ipv4"] == "5.6.7.8"


def test_detector_none_keeps_stored_value(app):
    app.detector.get_ipv4.return_value = "1.2.3.4"
    app.check_ip()
    app.notifications.send_to_all.reset_mock()
    # A transient detection failure must not wipe the stored address.
    app.detector.get_ipv4.return_value = None
    app.check_ip()
    app.notifications.send_to_all.assert_not_called()
    assert app.state.ipv4 == "1.2.3.4"


def test_outage_detection_and_recovery(config):
    config.events = EventsConfig(
        outage_detection_enabled=True, outage_threshold=2, notify_on_startup=False
    )
    app = Application(config)
    app.detector = MagicMock()
    app.notifications = MagicMock()
    app.notifications.providers = [MagicMock()]
    app.state = app.store.load()

    app.detector.get_ipv4.return_value = None
    app.check_ip()  # failure 1
    app.notifications.notify_event.assert_not_called()
    app.check_ip()  # failure 2 -> threshold reached
    assert app.notifications.notify_event.call_count == 1
    assert "Connectivity problem" in app.notifications.notify_event.call_args.args[0]

    # Recovery
    app.notifications.notify_event.reset_mock()
    app.detector.get_ipv4.return_value = "1.2.3.4"
    app.check_ip()
    assert app.notifications.notify_event.call_count == 1
    assert "Connectivity restored" in app.notifications.notify_event.call_args.args[0]


def test_run_exits_promptly_when_shutdown_set(app, monkeypatch):
    # Pre-set the shutdown event; run() should perform the initial check and
    # then exit the loop on the first wait() without blocking.
    app.detector.get_ipv4.return_value = "1.2.3.4"
    app.shutdown_event.set()
    rc = app.run()
    assert rc == 0


def test_next_wait_steady_state(app):
    # No failures: wait the full configured interval.
    app.consecutive_failures = 0
    assert app._next_wait() == float(app.config.check_interval)


def test_next_wait_backoff_grows(app, monkeypatch):
    monkeypatch.setattr(app, "_jitter", lambda: 0.0)
    app.consecutive_failures = 1
    assert app._next_wait() == 30
    app.consecutive_failures = 2
    assert app._next_wait() == 60
    app.consecutive_failures = 3
    assert app._next_wait() == 120


def test_next_wait_capped_at_interval(app, monkeypatch):
    monkeypatch.setattr(app, "_jitter", lambda: 0.0)
    # Many failures must never wait longer than the normal interval.
    app.consecutive_failures = 20
    assert app._next_wait() == float(app.config.check_interval)


def test_next_wait_includes_jitter(app, monkeypatch):
    monkeypatch.setattr(app, "_jitter", lambda: 2.5)
    app.consecutive_failures = 1
    assert app._next_wait() == 32.5


def test_heartbeat_emitted_when_due(config):
    config.events = EventsConfig(
        heartbeat_enabled=True, heartbeat_interval=0, notify_on_startup=False
    )
    app = Application(config)
    app.notifications = MagicMock()
    app.state.ipv4 = "1.2.3.4"
    app.maybe_heartbeat()
    app.notifications.notify_event.assert_called_once()
    assert app.notifications.notify_event.call_args.args[0] == "Heartbeat"


def test_status_snapshot_has_freshness_fields(app):
    app.detector.get_ipv4.return_value = "1.2.3.4"
    app.check_ip()
    snap = app.status_snapshot()
    assert snap["check_interval"] == app.config.check_interval
    assert isinstance(snap["seconds_since_last_check"], float)
    assert snap["seconds_since_last_check"] >= 0


def test_notification_exception_is_isolated(app):
    # A notifier blowing up must not count as a check failure or trigger outage.
    app.detector.get_ipv4.return_value = "1.2.3.4"
    app.notifications.send_to_all.side_effect = RuntimeError("notifier exploded")
    result = app.check_ip()
    assert result is True  # detection succeeded
    assert app.consecutive_failures == 0  # no false outage
    counters = app.metrics._counters
    failures = sum(
        v for (n, _), v in counters.items() if n == "wanwatcher_check_failures_total"
    )
    assert failures == 0


def test_geo_not_clobbered_by_failed_lookup(app, monkeypatch):
    app.detector.get_ipv4.return_value = "1.2.3.4"
    monkeypatch.setattr(
        "wanwatcher.app.get_geo_data", lambda *a, **k: {"city": "Lisbon"}
    )
    app.check_ip()  # first run, geo set
    assert app.geo_data == {"city": "Lisbon"}
    # A later change whose geo lookup fails must keep the previous geo.
    monkeypatch.setattr("wanwatcher.app.get_geo_data", lambda *a, **k: None)
    app.detector.get_ipv4.return_value = "5.6.7.8"
    app.check_ip()
    assert app.geo_data == {"city": "Lisbon"}


def test_status_snapshot_concurrent_with_check_is_consistent(app):
    import threading

    app.detector.get_ipv4.return_value = "1.2.3.4"
    app.check_ip()
    errors = []

    def reader():
        for _ in range(100):
            try:
                snap = app.status_snapshot()
                assert isinstance(snap["history"], list)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

    def writer():
        for i in range(100):
            app.detector.get_ipv4.return_value = f"1.2.3.{i % 254 + 1}"
            app.check_ip()

    t1, t2 = threading.Thread(target=reader), threading.Thread(target=writer)
    t1.start()
    t2.start()
    t1.join(5)
    t2.join(5)
    assert not errors
