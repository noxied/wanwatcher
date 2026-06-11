"""Telegram bot notification provider.

The bot token is stored privately and the API URL is built at request time
so the token never appears in attributes, logs, or exception messages.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from wanwatcher.notifiers.base import NotificationProvider

logger = logging.getLogger(__name__)


class TelegramNotifier(NotificationProvider):
    """Telegram bot notification provider."""

    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str, parse_mode: str = "HTML"):
        self._bot_token = bot_token
        self.chat_id = chat_id
        self.parse_mode = parse_mode

    def _post(self, payload: Dict[str, Any]) -> Optional[requests.Response]:
        """Post a payload to the Telegram API.

        The URL embeds the bot token, so it is built here and never stored.
        Returns None on a transport error; never lets the token leak into
        log output (requests exceptions include the full request URL).
        """
        api_url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        try:
            return requests.post(api_url, json=payload, timeout=10)
        except requests.RequestException as exc:
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)
            if status is not None:
                logger.error(
                    "Telegram request failed: %s (Status: %s)",
                    type(exc).__name__,
                    status,
                )
            else:
                logger.error("Telegram request failed: %s", type(exc).__name__)
            return None

    def send_notification(
        self,
        current_ips: Dict[str, Optional[str]],
        previous_ips: Dict[str, Optional[str]],
        geo_data: Optional[Dict[str, Any]],
        is_first_run: bool,
        server_name: str,
        version: str = "",
    ) -> bool:
        """Send Telegram notification."""
        try:
            # Determine notification type
            if is_first_run:
                title = "✅ Initial IP Detection"
                emoji = "🟢"
            else:
                title = "🔄 IP Address Changed"
                emoji = "🟠"

            # Build message
            message_lines = [
                f"{emoji} <b>WAN IP Monitor Alert</b>",
                f"<b>{title}</b>",
                f"Monitoring for <b>{server_name}</b>",
                "",
            ]

            # IP Change details (if not first run)
            if not is_first_run:
                message_lines.append("<b>📊 Changes Detected:</b>")
                if current_ips.get("ipv4") != previous_ips.get("ipv4"):
                    message_lines.append(
                        f"  • IPv4: <code>{previous_ips.get('ipv4', 'None')}</code> → "
                        f"<code>{current_ips.get('ipv4', 'None')}</code>"
                    )
                if current_ips.get("ipv6") != previous_ips.get("ipv6"):
                    message_lines.append(
                        f"  • IPv6: <code>{previous_ips.get('ipv6', 'None')}</code> → "
                        f"<code>{current_ips.get('ipv6', 'None')}</code>"
                    )
                message_lines.append("")

            # Current IPs
            if current_ips.get("ipv4"):
                message_lines.append(
                    f"<b>📍 Current IPv4:</b>\n<code>{current_ips['ipv4']}</code>"
                )
                message_lines.append("")

            if current_ips.get("ipv6"):
                message_lines.append(
                    f"<b>📍 Current IPv6:</b>\n<code>{current_ips['ipv6']}</code>"
                )
                message_lines.append("")

            # Geographic information
            if geo_data:
                message_lines.append("<b>📍 Location Information</b>")
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
                    message_lines.append(f"🌍 {location}")

                if geo_data.get("org"):
                    message_lines.append(f"🏢 {geo_data['org']}")

                if geo_data.get("timezone"):
                    message_lines.append(f"🕐 {geo_data['timezone']}")

                message_lines.append("")

            # Metadata
            detected_at = datetime.now().strftime("%A, %B %d, %Y at %H:%M:%S")
            message_lines.extend(
                [
                    f"<b>⏰ Detected At:</b> {detected_at}",
                    "<b>🐳 Environment:</b> Running in Docker",
                    f"<b>📦 Version:</b> v{version}",
                ]
            )

            message = "\n".join(message_lines)

            # Send message
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": self.parse_mode,
            }

            response = self._post(payload)
            if response is None:
                return False

            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
                return True

            logger.error(
                "Telegram notification failed (Status: %d): %s",
                response.status_code,
                response.text,
            )
            return False

        except requests.RequestException as exc:
            logger.error("Failed to send Telegram notification: %s", type(exc).__name__)
            return False
        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error("Failed to send Telegram notification: %s", type(exc).__name__)
            return False

    def send_update_notification(
        self, update_info: Dict[str, str], server_name: str, version: str = ""
    ) -> bool:
        """Send Telegram update notification."""
        try:
            # Extract changelog highlights
            changelog = update_info.get("release_body", "")
            changelog_lines = []
            for line in changelog.split("\n")[:8]:
                line = line.strip()
                if line and (
                    line.startswith("- ")
                    or line.startswith("* ")
                    or line.startswith("• ")
                ):
                    cleaned = line.lstrip("-*• ").strip()
                    if cleaned and not cleaned.startswith("#"):
                        changelog_lines.append(f"  • {cleaned}")

            changelog_preview = (
                "\n".join(changelog_lines[:5])
                if changelog_lines
                else "See release notes for details"
            )

            # Build message
            message_lines = [
                "🆕 <b>WANwatcher Update Available!</b>",
                "",
                f"<b>Current Version:</b> v{update_info['current_version']}",
                f"<b>Latest Version:</b> v{update_info['latest_version']}",
                "",
                "<b>📋 What's New:</b>",
                changelog_preview,
                "",
                "<b>🔗 Full Changelog:</b>",
                f"<a href=\"{update_info['release_url']}\">View Release Notes</a>",
                "",
                "<b>💡 How to Update:</b>",
                "<code>docker pull noxied/wanwatcher:latest</code>",
                "<code>docker restart wanwatcher</code>",
                "",
                f"<i>Update check for {server_name}</i>",
            ]

            message = "\n".join(message_lines)

            # Send message
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": self.parse_mode,
                "disable_web_page_preview": False,
            }

            response = self._post(payload)
            if response is None:
                return False

            if response.status_code == 200:
                logger.info("Telegram update notification sent successfully")
                return True

            logger.error(
                "Telegram update notification failed (Status: %d)",
                response.status_code,
            )
            return False

        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error(
                "Failed to send Telegram update notification: %s", type(exc).__name__
            )
            return False

    def send_event(
        self,
        title: str,
        message: str,
        server_name: str,
        severity: str = "info",
    ) -> bool:
        """Send a generic event as an HTML text message."""
        try:
            text = f"<b>{title}</b>\n\n{message}\n\n<i>{server_name}</i>"

            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": self.parse_mode,
            }

            response = self._post(payload)
            if response is None:
                return False

            if response.status_code == 200:
                logger.info("Telegram event notification sent successfully")
                return True

            logger.error(
                "Telegram event notification failed (Status: %d)",
                response.status_code,
            )
            return False

        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error(
                "Failed to send Telegram event notification: %s", type(exc).__name__
            )
            return False
