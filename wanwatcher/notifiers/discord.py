"""Discord webhook notification provider."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from wanwatcher.notifiers.base import NotificationProvider

logger = logging.getLogger(__name__)

# Embed colors for send_event severities
_SEVERITY_COLORS: Dict[str, int] = {
    "info": 3447003,  # Blue
    "warning": 15105570,  # Orange
    "error": 15158332,  # Red
}


class DiscordNotifier(NotificationProvider):
    """Discord webhook notification provider with custom avatar support."""

    name = "discord"

    def __init__(
        self, webhook_url: str, bot_name: str = "WANwatcher", avatar_url: str = ""
    ):
        self.webhook_url = webhook_url
        self.bot_name = bot_name
        self.avatar_url = avatar_url
        self.default_avatar_path = "/app/avatar.png"

    def _get_avatar_url(self) -> str:
        """Get avatar URL - custom or use webhook's configured avatar."""
        # If custom avatar URL is provided via environment variable, use it
        if self.avatar_url:
            return self.avatar_url

        # Return empty to use webhook's configured avatar (set in Discord
        # webhook settings). This is the best approach as it respects the
        # webhook's configuration. Users can set the avatar in Discord:
        # Server Settings > Integrations > Webhooks > Edit
        return ""

    def _post(self, payload: Dict[str, Any]) -> requests.Response:
        """Post a payload to the webhook."""
        return requests.post(self.webhook_url, json=payload, timeout=10)

    def send_notification(
        self,
        current_ips: Dict[str, Optional[str]],
        previous_ips: Dict[str, Optional[str]],
        geo_data: Optional[Dict[str, Any]],
        is_first_run: bool,
        server_name: str,
        version: str = "",
    ) -> bool:
        """Send Discord webhook notification."""
        try:
            # Determine notification type
            if is_first_run:
                title = "✅ Initial IP Detection"
                color = 0x00FF00  # Green
                change_info = f"Monitoring started for **{server_name}**"
            else:
                title = "🔄 IP Address Changed"
                color = 0xFF9900  # Orange

                # Build change details
                changes = []
                if current_ips.get("ipv4") != previous_ips.get("ipv4"):
                    changes.append(
                        f"**IPv4:** `{previous_ips.get('ipv4', 'None')}` → "
                        f"`{current_ips.get('ipv4', 'None')}`"
                    )
                if current_ips.get("ipv6") != previous_ips.get("ipv6"):
                    changes.append(
                        f"**IPv6:** `{previous_ips.get('ipv6', 'None')}` → "
                        f"`{current_ips.get('ipv6', 'None')}`"
                    )

                change_info = (
                    "\n".join(changes) if changes else "IP information updated"
                )

            # Build embed fields
            fields: List[Dict[str, Any]] = []

            # Current IPs
            if current_ips.get("ipv4"):
                fields.append(
                    {
                        "name": "📍 Current IPv4",
                        "value": f"`{current_ips['ipv4']}`",
                        "inline": False,
                    }
                )

            if current_ips.get("ipv6"):
                fields.append(
                    {
                        "name": "📍 Current IPv6",
                        "value": f"`{current_ips['ipv6']}`",
                        "inline": False,
                    }
                )

            # Geographic information
            if geo_data:
                geo_text = []
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
                    geo_text.append(f"🌍 {location}")

                if geo_data.get("org"):
                    geo_text.append(f"🏢 {geo_data['org']}")

                if geo_data.get("timezone"):
                    geo_text.append(f"🕐 {geo_data['timezone']}")

                if geo_text:
                    fields.append(
                        {
                            "name": "📍 Location Information",
                            "value": "\n".join(geo_text),
                            "inline": False,
                        }
                    )

            # Detection time and environment
            fields.append(
                {
                    "name": "⏰ Detected At",
                    "value": datetime.now().strftime("%A, %B %d, %Y at %H:%M:%S"),
                    "inline": False,
                }
            )

            fields.append(
                {"name": "🐳 Environment", "value": "Running in Docker", "inline": True}
            )

            fields.append(
                {"name": "📦 Version", "value": f"v{version}", "inline": True}
            )

            # Build payload
            payload: Dict[str, Any] = {
                "username": self.bot_name,
                "embeds": [
                    {
                        "title": "🌐 WAN IP Monitor Alert",
                        "description": f"**{title}**\n\n{change_info}",
                        "color": color,
                        "fields": fields,
                        "footer": {"text": f"WANwatcher v{version} on {server_name}"},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            }

            # Only include avatar_url if custom avatar is provided
            # Otherwise Discord uses the webhook's configured avatar
            avatar_url = self._get_avatar_url()
            if avatar_url:
                payload["avatar_url"] = avatar_url

            # Send webhook
            response = self._post(payload)

            if response.status_code == 204:
                logger.info(
                    "Discord notification sent successfully (Status: %d)",
                    response.status_code,
                )
                return True

            logger.error(
                "Discord notification failed (Status: %d): %s",
                response.status_code,
                response.text,
            )
            return False

        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error("Failed to send Discord notification: %s", exc)
            return False

    def send_update_notification(
        self, update_info: Dict[str, str], server_name: str, version: str = ""
    ) -> bool:
        """Send Discord update notification."""
        try:
            # Extract changelog highlights (first few bullet points)
            changelog = update_info.get("release_body", "")
            changelog_lines = []
            for line in changelog.split("\n")[:15]:  # Check more lines
                line = line.strip()
                if line and (
                    line.startswith("- ")
                    or line.startswith("* ")
                    or line.startswith("• ")
                ):
                    # Clean up markdown list markers
                    cleaned = line.lstrip("-*• ").strip()
                    if (
                        cleaned and not cleaned.startswith("#") and len(cleaned) < 100
                    ):  # Skip headers and long lines
                        # Truncate if still too long
                        if len(cleaned) > 80:
                            cleaned = cleaned[:77] + "..."
                        changelog_lines.append(f"• {cleaned}")

                # Stop if we have enough
                if len(changelog_lines) >= 4:
                    break

            # Build preview with character limit (Discord field limit is 1024)
            changelog_preview = ""
            for line in changelog_lines[:4]:
                if len(changelog_preview) + len(line) + 1 < 900:  # Leave some margin
                    changelog_preview += line + "\n"
                else:
                    break

            if not changelog_preview.strip():
                changelog_preview = "See release notes for details"

            embed = {
                "title": "🆕 WANwatcher Update Available!",
                "description": "A new version of WANwatcher is ready to install.",
                "color": 0x00D9FF,  # Cyan
                "fields": [
                    {
                        "name": "📦 Current Version",
                        "value": f"`v{update_info['current_version']}`",
                        "inline": True,
                    },
                    {
                        "name": "🎁 Latest Version",
                        "value": f"`v{update_info['latest_version']}`",
                        "inline": True,
                    },
                    {
                        "name": "\u200b",  # Empty field for spacing
                        "value": "\u200b",
                        "inline": False,
                    },
                    {
                        "name": "📋 What's New",
                        "value": changelog_preview.strip(),
                        "inline": False,
                    },
                    {
                        "name": "🔗 Full Changelog",
                        "value": f"[View Release Notes]({update_info['release_url']})",
                        "inline": False,
                    },
                    {
                        "name": "💡 How to Update",
                        "value": (
                            "```bash\ndocker pull noxied/wanwatcher:latest\n"
                            "docker restart wanwatcher\n```"
                        ),
                        "inline": False,
                    },
                ],
                "footer": {"text": f"Update check for {server_name}"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            payload: Dict[str, Any] = {"username": self.bot_name, "embeds": [embed]}

            # Only include avatar_url if custom avatar is provided
            avatar_url = self._get_avatar_url()
            if avatar_url:
                payload["avatar_url"] = avatar_url

            response = self._post(payload)

            if response.status_code == 204:
                logger.info("Discord update notification sent successfully")
                return True

            logger.error(
                "Discord update notification failed (Status: %d)",
                response.status_code,
            )
            return False

        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error("Failed to send Discord update notification: %s", exc)
            return False

    def send_event(
        self,
        title: str,
        message: str,
        server_name: str,
        severity: str = "info",
    ) -> bool:
        """Send a simple event embed colored by severity."""
        try:
            color = _SEVERITY_COLORS.get(severity, _SEVERITY_COLORS["info"])

            payload: Dict[str, Any] = {
                "username": self.bot_name,
                "embeds": [
                    {
                        "title": title,
                        "description": message,
                        "color": color,
                        "footer": {"text": server_name},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            }

            avatar_url = self._get_avatar_url()
            if avatar_url:
                payload["avatar_url"] = avatar_url

            response = self._post(payload)

            if response.status_code == 204:
                logger.info("Discord event notification sent successfully")
                return True

            logger.error(
                "Discord event notification failed (Status: %d)",
                response.status_code,
            )
            return False

        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error("Failed to send Discord event notification: %s", exc)
            return False
