"""Apprise notification provider.

Apprise (https://github.com/caronc/apprise) bridges 100+ notification
services through URL strings (ntfy://, pover://, slack://, ...). The
`apprise` package is an optional dependency: it is imported lazily inside
__init__ so the rest of the application works without it installed.

Apprise URLs frequently embed credentials, so they are never logged in
full - only the scheme/service prefix before "://".
"""

import logging
from typing import Any, Dict, List, Optional

from wanwatcher.notifiers.base import NotificationProvider

logger = logging.getLogger(__name__)


def _url_scheme(url: str) -> str:
    """Return only the scheme part of an Apprise URL (safe to log)."""
    return url.split("://", 1)[0] if "://" in url else "(no scheme)"


class AppriseNotifier(NotificationProvider):
    """Notification provider backed by the apprise library."""

    name = "apprise"

    def __init__(self, urls: List[str], bot_name: str = "WANwatcher"):
        try:
            import apprise  # noqa: PLC0415 - lazy import, optional dependency
        except ImportError as exc:
            raise ImportError(
                "The 'apprise' package is required for AppriseNotifier "
                "(pip install apprise)"
            ) from exc

        self._apprise_module = apprise
        self.bot_name = bot_name
        self._apprise = apprise.Apprise()

        for url in urls:
            if not self._apprise.add(url):
                # Never log the full URL: it can contain credentials.
                logger.warning(
                    "Failed to add Apprise URL with scheme '%s'", _url_scheme(url)
                )

    def _notify_type(self, severity: str) -> Any:
        """Map a severity string to an apprise.NotifyType."""
        notify_type = self._apprise_module.NotifyType
        mapping = {
            "info": notify_type.INFO,
            "warning": notify_type.WARNING,
            "error": notify_type.FAILURE,
        }
        return mapping.get(severity, notify_type.INFO)

    def send_notification(
        self,
        current_ips: Dict[str, Optional[str]],
        previous_ips: Dict[str, Optional[str]],
        geo_data: Optional[Dict[str, Any]],
        is_first_run: bool,
        server_name: str,
        version: str = "",
    ) -> bool:
        """Send an IP change notification through all configured services."""
        try:
            if is_first_run:
                title = "WANwatcher started monitoring"
                body_lines = [f"Monitoring started for {server_name}", ""]
            else:
                title = "IP address changed"
                body_lines = ["Changes detected:"]
                if current_ips.get("ipv4") != previous_ips.get("ipv4"):
                    body_lines.append(
                        f"  IPv4: {previous_ips.get('ipv4', 'None')} → "
                        f"{current_ips.get('ipv4', 'None')}"
                    )
                if current_ips.get("ipv6") != previous_ips.get("ipv6"):
                    body_lines.append(
                        f"  IPv6: {previous_ips.get('ipv6', 'None')} → "
                        f"{current_ips.get('ipv6', 'None')}"
                    )
                body_lines.append("")

            if current_ips.get("ipv4"):
                body_lines.append(f"Current IPv4: {current_ips['ipv4']}")
            if current_ips.get("ipv6"):
                body_lines.append(f"Current IPv6: {current_ips['ipv6']}")

            if geo_data:
                body_lines.append("")
                if (
                    geo_data.get("city")
                    or geo_data.get("region")
                    or geo_data.get("country")
                ):
                    location = ", ".join(
                        filter(
                            None,
                            [
                                geo_data.get("city"),
                                geo_data.get("region"),
                                geo_data.get("country"),
                            ],
                        )
                    )
                    body_lines.append(f"Location: {location}")
                if geo_data.get("org"):
                    body_lines.append(f"ISP: {geo_data['org']}")
                if geo_data.get("timezone"):
                    body_lines.append(f"Timezone: {geo_data['timezone']}")

            body_lines.extend(
                [
                    "",
                    f"Server: {server_name}",
                    f"WANwatcher v{version}",
                ]
            )

            body = "\n".join(body_lines)

            result = bool(
                self._apprise.notify(
                    title=title, body=body, notify_type=self._notify_type("info")
                )
            )

            if result:
                logger.info("Apprise notification sent successfully")
            else:
                logger.error("Apprise notification failed")
            return result

        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error("Failed to send Apprise notification: %s", exc)
            return False

    def send_update_notification(
        self, update_info: Dict[str, str], server_name: str, version: str = ""
    ) -> bool:
        """Send an update-available notification."""
        try:
            title = "WANwatcher update available"
            body = "\n".join(
                [
                    f"Current version: v{update_info['current_version']}",
                    f"Latest version: v{update_info['latest_version']}",
                    "",
                    f"Release notes: {update_info['release_url']}",
                    "",
                    f"Update check for {server_name}",
                ]
            )

            result = bool(
                self._apprise.notify(
                    title=title, body=body, notify_type=self._notify_type("info")
                )
            )

            if result:
                logger.info("Apprise update notification sent successfully")
            else:
                logger.error("Apprise update notification failed")
            return result

        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error("Failed to send Apprise update notification: %s", exc)
            return False

    def send_event(
        self,
        title: str,
        message: str,
        server_name: str,
        severity: str = "info",
    ) -> bool:
        """Send a generic event with severity mapped to an Apprise type."""
        try:
            body = f"{message}\n\n{server_name}"

            result = bool(
                self._apprise.notify(
                    title=title, body=body, notify_type=self._notify_type(severity)
                )
            )

            if result:
                logger.info("Apprise event notification sent successfully")
            else:
                logger.error("Apprise event notification failed")
            return result

        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error("Failed to send Apprise event notification: %s", exc)
            return False
