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
