"""Tests for the MQTT publisher.

paho-mqtt is required for instantiation; if it is not installed these tests
are skipped. The network client is replaced with a mock so no broker is hit.
"""

import json
from unittest.mock import MagicMock

import pytest

paho = pytest.importorskip("paho.mqtt.client")

from wanwatcher.config import MQTTConfig  # noqa: E402
from wanwatcher.mqtt import MQTTPublisher, _slugify  # noqa: E402


def test_slugify():
    assert _slugify("My Test-Server!") == "my_test_server"
    assert _slugify("") == "wanwatcher"


@pytest.fixture
def publisher():
    cfg = MQTTConfig(enabled=True, host="broker", port=1883, topic_prefix="wanwatcher")
    pub = MQTTPublisher(cfg, server_name="My Server")
    pub._client = MagicMock()
    return pub


def test_start_connects(publisher):
    publisher.start()
    publisher._client.connect_async.assert_called_once_with("broker", 1883)
    publisher._client.loop_start.assert_called_once()


def test_publish_state_skipped_when_disconnected(publisher):
    publisher.publish_state("1.2.3.4", None, None, None)
    publisher._client.publish.assert_not_called()


def test_publish_state_when_connected(publisher):
    publisher._connected.set()
    publisher.publish_state("1.2.3.4", "2001:db8::1", {"city": "Lisbon"}, "2026-01-01")
    topics = {c.args[0] for c in publisher._client.publish.call_args_list}
    assert "wanwatcher/ipv4" in topics
    assert "wanwatcher/state" in topics
    state_call = next(
        c
        for c in publisher._client.publish.call_args_list
        if c.args[0] == "wanwatcher/state"
    )
    payload = json.loads(state_call.kwargs["payload"])
    assert payload["ipv4"] == "1.2.3.4"
    assert payload["geo"]["city"] == "Lisbon"


def test_stop_publishes_offline(publisher):
    publisher.stop()
    offline = [
        c
        for c in publisher._client.publish.call_args_list
        if c.args[0] == "wanwatcher/availability"
    ]
    assert offline
    publisher._client.loop_stop.assert_called_once()


def test_start_never_raises(publisher):
    publisher._client.connect_async.side_effect = OSError("broker down")
    publisher.start()  # must not raise
