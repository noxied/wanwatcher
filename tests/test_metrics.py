"""Tests for the in-process metrics registry."""

from wanwatcher.metrics import Metrics


def test_inc_and_render():
    m = Metrics()
    m.inc("wanwatcher_checks_total")
    m.inc("wanwatcher_checks_total")
    out = m.render()
    assert "wanwatcher_checks_total 2" in out
    assert "# HELP wanwatcher_checks_total" in out
    assert "# TYPE wanwatcher_checks_total counter" in out


def test_inc_with_value():
    m = Metrics()
    m.inc("wanwatcher_checks_total", value=5)
    assert "wanwatcher_checks_total 5" in m.render()


def test_labels_render():
    m = Metrics()
    m.inc("wanwatcher_ip_changes_total", {"family": "ipv4"})
    m.inc("wanwatcher_ip_changes_total", {"family": "ipv6"})
    out = m.render()
    assert 'wanwatcher_ip_changes_total{family="ipv4"} 1' in out
    assert 'wanwatcher_ip_changes_total{family="ipv6"} 1' in out


def test_label_independence():
    m = Metrics()
    m.inc("wanwatcher_notifications_total", {"provider": "Discord", "result": "ok"})
    m.inc("wanwatcher_notifications_total", {"provider": "Discord", "result": "ok"})
    m.inc("wanwatcher_notifications_total", {"provider": "Telegram", "result": "error"})
    out = m.render()
    assert 'provider="Discord",result="ok"} 2' in out
    assert 'provider="Telegram",result="error"} 1' in out


def test_set_gauge_overwrites():
    m = Metrics()
    m.set_gauge("wanwatcher_up", 1)
    m.set_gauge("wanwatcher_up", 0)
    lines = [
        line for line in m.render().splitlines() if line.startswith("wanwatcher_up ")
    ]
    assert lines == ["wanwatcher_up 0"]


def test_help_emitted_once_per_metric():
    m = Metrics()
    m.inc("wanwatcher_ip_changes_total", {"family": "ipv4"})
    m.inc("wanwatcher_ip_changes_total", {"family": "ipv6"})
    out = m.render()
    assert out.count("# HELP wanwatcher_ip_changes_total") == 1


def test_startup_gauges_present():
    out = Metrics().render()
    assert "wanwatcher_up 1" in out
    assert "wanwatcher_start_time_seconds" in out
