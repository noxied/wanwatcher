"""Aggregates notification providers and fans messages out with retries."""

import logging
from typing import Any, Dict, List, Optional

from wanwatcher.notifiers.base import NotificationProvider, retry_with_backoff

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self) -> None:
        self.providers: List[NotificationProvider] = []

    def add_provider(self, provider: NotificationProvider) -> None:
        self.providers.append(provider)

    def _fan_out(self, action_name: str, call) -> Dict[str, bool]:
        """Run `call(provider)` for each provider with retry; collect results."""
        results: Dict[str, bool] = {}
        for provider in self.providers:
            provider_name = provider.__class__.__name__
            logger.info("Sending %s via %s...", action_name, provider_name)
            success = retry_with_backoff(
                lambda p=provider: call(p), max_retries=3, base_delay=2.0
            )
            results[provider_name] = success
            if success:
                logger.info("%s %s sent successfully", provider_name, action_name)
            else:
                logger.error(
                    "%s %s failed after all retries", provider_name, action_name
                )
        return results

    def send_to_all(
        self,
        current_ips: Dict[str, Optional[str]],
        previous_ips: Dict[str, Optional[str]],
        geo_data: Optional[Dict[str, Any]],
        is_first_run: bool,
        server_name: str,
        version: str = "",
    ) -> Dict[str, bool]:
        return self._fan_out(
            "notification",
            lambda p: p.send_notification(
                current_ips, previous_ips, geo_data, is_first_run, server_name, version
            ),
        )

    def notify_update(
        self, update_info: Dict[str, str], server_name: str, version: str = ""
    ) -> Dict[str, bool]:
        return self._fan_out(
            "update notification",
            lambda p: p.send_update_notification(update_info, server_name, version),
        )

    def notify_event(
        self, title: str, message: str, server_name: str, severity: str = "info"
    ) -> Dict[str, bool]:
        return self._fan_out(
            f"event ({title})",
            lambda p: p.send_event(title, message, server_name, severity),
        )

    # Backward-compatible alias used by v1 call sites and tests
    def notify_all(
        self,
        current_ips: Dict[str, Optional[str]],
        previous_ips: Dict[str, Optional[str]],
        geo_data: Optional[Dict[str, Any]],
        is_first_run: bool,
        server_name: str,
        version: str = "",
    ) -> Dict[str, bool]:
        return self.send_to_all(
            current_ips, previous_ips, geo_data, is_first_run, server_name, version
        )

    def notify_error(self, error_msg: str, server_name: str) -> None:
        logger.error("Error notification: %s", error_msg)
