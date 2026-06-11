"""MQTT publisher with Home Assistant discovery for WANwatcher.

Publishes the current WAN IPs (retained) under a configurable topic prefix and,
optionally, Home Assistant MQTT discovery configs so the sensors appear
automatically. The paho-mqtt dependency is imported lazily so the rest of the
application works without it; instantiating :class:`MQTTPublisher` without
paho-mqtt installed raises a clear ImportError.

All public methods are defensive: a broker outage or a misbehaving client must
never crash the monitoring loop, so errors are caught and logged.
"""

from __future__ import annotations

import json
import logging
import re
import ssl
import threading
from typing import Any, Dict, Optional

from wanwatcher import VERSION
from wanwatcher.config import MQTTConfig

logger = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    """Lowercase and replace runs of non-alphanumeric characters with '_'."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "wanwatcher"


class MQTTPublisher:
    """Publishes WAN IP state to an MQTT broker, with HA discovery support."""

    def __init__(self, config: MQTTConfig, server_name: str) -> None:
        self.config = config
        self.server_name = server_name
        self.node_id = _slugify(server_name)
        self._prefix = config.topic_prefix.rstrip("/")
        self._availability_topic = f"{self._prefix}/availability"
        self._connected = threading.Event()

        try:
            import paho.mqtt.client as mqtt  # noqa: PLC0415 (lazy by design)
        except ImportError as exc:
            raise ImportError(
                "MQTT support requires the 'paho-mqtt' package. "
                "Install it with: pip install paho-mqtt"
            ) from exc

        self._mqtt = mqtt
        callback_api = getattr(mqtt, "CallbackAPIVersion", None)
        if callback_api is not None:
            # paho-mqtt >= 2.0
            self._client = mqtt.Client(
                callback_api_version=callback_api.VERSION2,
                client_id=config.client_id,
            )
        else:
            # paho-mqtt 1.x
            self._client = mqtt.Client(client_id=config.client_id)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        """Connect asynchronously and start the network loop.

        Never raises: a broker outage must not block or crash the app.
        """
        try:
            if self.config.username:
                self._client.username_pw_set(
                    self.config.username, self.config.password or None
                )
            if self.config.tls:
                self._client.tls_set_context(ssl.create_default_context())
            self._client.will_set(
                self._availability_topic, payload="offline", retain=True
            )
            self._client.connect_async(self.config.host, self.config.port)
            self._client.loop_start()
            logger.info(
                "MQTT: connecting to %s:%s as '%s'",
                self.config.host,
                self.config.port,
                self.config.client_id,
            )
        except Exception:  # noqa: BLE001 - never propagate out of start()
            logger.exception("MQTT: failed to start client")

    def stop(self) -> None:
        """Publish offline status and shut the client down. Never raises."""
        try:
            self._client.publish(
                self._availability_topic, payload="offline", retain=True
            )
        except Exception:  # noqa: BLE001
            logger.debug("MQTT: failed to publish offline status", exc_info=True)
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:  # noqa: BLE001
            logger.debug("MQTT: error during disconnect", exc_info=True)
        self._connected.clear()
        logger.info("MQTT: stopped")

    # -- publishing ----------------------------------------------------------

    def publish_state(
        self,
        ipv4: Optional[str],
        ipv6: Optional[str],
        geo: Optional[Dict[str, Any]],
        last_change: Optional[str],
    ) -> None:
        """Publish the current WAN state as retained messages. Never raises."""
        if not self._connected.is_set():
            logger.debug("MQTT: not connected, skipping state publish")
            return
        try:
            self._publish(f"{self._prefix}/ipv4", ipv4 or "")
            self._publish(f"{self._prefix}/ipv6", ipv6 or "")
            self._publish(f"{self._prefix}/last_change", last_change or "")
            state = {
                "ipv4": ipv4,
                "ipv6": ipv6,
                "last_change": last_change,
                "geo": geo if geo else None,
                "server_name": self.server_name,
            }
            self._publish(f"{self._prefix}/state", json.dumps(state))
            logger.debug("MQTT: state published to %s/*", self._prefix)
        except Exception:  # noqa: BLE001
            logger.exception("MQTT: failed to publish state")

    def _publish(self, topic: str, payload: str) -> None:
        self._client.publish(topic, payload=payload, retain=True)

    # -- callbacks -----------------------------------------------------------

    def _on_connect(self, *args: Any, **kwargs: Any) -> None:
        """Handle connect for both paho v1 (rc) and v2 (reason_code) APIs."""
        # v1: (client, userdata, flags, rc)
        # v2: (client, userdata, flags, reason_code, properties)
        reason = args[3] if len(args) > 3 else None
        failed = False
        if reason is not None:
            try:
                failed = bool(
                    reason.is_failure
                    if hasattr(reason, "is_failure")
                    else int(reason) != 0
                )
            except (TypeError, ValueError):
                failed = False
        if failed:
            logger.warning("MQTT: connection refused (%s)", reason)
            return

        self._connected.set()
        logger.info("MQTT: connected to %s:%s", self.config.host, self.config.port)
        try:
            self._publish(self._availability_topic, "online")
            if self.config.ha_discovery:
                self._publish_discovery()
        except Exception:  # noqa: BLE001
            logger.exception("MQTT: failed to publish on-connect messages")

    def _on_disconnect(self, *args: Any, **kwargs: Any) -> None:
        self._connected.clear()
        logger.warning("MQTT: disconnected from broker, will auto-reconnect")

    # -- Home Assistant discovery ---------------------------------------------

    def _publish_discovery(self) -> None:
        """Publish retained HA MQTT discovery configs for the WAN sensors."""
        device = {
            "identifiers": [f"wanwatcher_{self.node_id}"],
            "name": self.server_name,
            "manufacturer": "WANwatcher",
            "model": "WAN IP monitor",
            "sw_version": VERSION,
        }
        sensors = [
            ("wan_ipv4", "WAN IPv4", f"{self._prefix}/ipv4", None),
            ("wan_ipv6", "WAN IPv6", f"{self._prefix}/ipv6", None),
            (
                "wan_last_change",
                "WAN last change",
                f"{self._prefix}/last_change",
                "timestamp",
            ),
        ]
        for object_id, name, state_topic, device_class in sensors:
            payload: Dict[str, Any] = {
                "name": name,
                "unique_id": f"{self.node_id}_{object_id}",
                "state_topic": state_topic,
                "availability_topic": self._availability_topic,
                "icon": "mdi:ip-network",
                "device": device,
            }
            if device_class:
                payload["device_class"] = device_class
            topic = (
                f"{self.config.ha_discovery_prefix}/sensor/"
                f"{self.node_id}/{object_id}/config"
            )
            self._publish(topic, json.dumps(payload))
        logger.info(
            "MQTT: Home Assistant discovery configs published under %s/sensor/%s/*",
            self.config.ha_discovery_prefix,
            self.node_id,
        )
