"""
WANwatcher Notification Providers v1.4.1
Supports Discord, Telegram, and Email notifications
"""

import base64
import json
import logging
import os
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Callable, Dict, List, Optional, Union

import requests

logger = logging.getLogger(__name__)


def retry_with_backoff(func: Callable, max_retries: int = 3, base_delay: float = 1.0) -> bool:
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to retry (should return bool for success)
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)

    Returns:
        bool: True if function succeeded, False if all retries failed
    """
    for attempt in range(max_retries):
        try:
            result = func()
            if result:
                return True

            # If function returned False but didn't raise exception
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
                time.sleep(delay)
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed with error: {e}, retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} attempts failed: {e}")
                return False

    return False


class NotificationProvider:
    """Base class for notification providers"""

    def send_notification(self, current_ips: Dict[str, Optional[str]],
                         previous_ips: Dict[str, Optional[str]],
                         geo_data: Optional[Dict[str, Any]],
                         is_first_run: bool,
                         server_name: str) -> bool:
        """Send notification - to be implemented by subclasses"""
        raise NotImplementedError

    def send_update_notification(self, update_info: Dict[str, str], server_name: str, version: str = "1.4.0") -> bool:
        """Send update notification - to be implemented by subclasses"""
        raise NotImplementedError


class DiscordNotifier(NotificationProvider):
    """Discord webhook notification provider with custom avatar support"""

    def __init__(self, webhook_url: str, bot_name: str = "WANwatcher", avatar_url: str = ""):
        self.webhook_url = webhook_url
        self.bot_name = bot_name
        self.avatar_url = avatar_url
        self.default_avatar_path = "/app/avatar.png"

    def _get_avatar_url(self) -> str:
        """Get avatar URL - custom or use webhook's configured avatar"""
        # If custom avatar URL is provided via environment variable, use it
        if self.avatar_url:
            return self.avatar_url

        # Return empty to use webhook's configured avatar (set in Discord webhook settings)
        # This is the best approach as it respects the webhook's configuration
        # Users can set avatar in Discord: Server Settings > Integrations > Webhooks > Edit
        return ""

    def send_notification(self, current_ips: Dict[str, Optional[str]],
                         previous_ips: Dict[str, Optional[str]],
                         geo_data: Optional[Dict[str, Any]],
                         is_first_run: bool,
                         server_name: str,
                         version: str = "1.4.0") -> bool:
        """Send Discord webhook notification"""
        try:
            # Determine notification type
            if is_first_run:
                title = "✅ Initial IP Detection"
                color = 0x00ff00  # Green
                change_info = f"Monitoring started for **{server_name}**"
            else:
                title = "🔄 IP Address Changed"
                color = 0xff9900  # Orange

                # Build change details
                changes = []
                if current_ips.get('ipv4') != previous_ips.get('ipv4'):
                    changes.append(f"**IPv4:** `{previous_ips.get('ipv4', 'None')}` → `{current_ips.get('ipv4', 'None')}`")
                if current_ips.get('ipv6') != previous_ips.get('ipv6'):
                    changes.append(f"**IPv6:** `{previous_ips.get('ipv6', 'None')}` → `{current_ips.get('ipv6', 'None')}`")

                change_info = "\n".join(changes) if changes else "IP information updated"

            # Build embed fields
            fields = []

            # Current IPs
            if current_ips.get('ipv4'):
                fields.append({
                    "name": "📍 Current IPv4",
                    "value": f"`{current_ips['ipv4']}`",
                    "inline": False
                })

            if current_ips.get('ipv6'):
                fields.append({
                    "name": "📍 Current IPv6",
                    "value": f"`{current_ips['ipv6']}`",
                    "inline": False
                })

            # Geographic information
            if geo_data:
                geo_text = []
                if geo_data.get('city') or geo_data.get('region') or geo_data.get('country'):
                    location = ", ".join(filter(None, [
                        geo_data.get('city'),
                        geo_data.get('region'),
                        geo_data.get('country')
                    ]))
                    geo_text.append(f"🌍 {location}")

                if geo_data.get('org'):
                    geo_text.append(f"🏢 {geo_data['org']}")

                if geo_data.get('timezone'):
                    geo_text.append(f"🕐 {geo_data['timezone']}")

                if geo_text:
                    fields.append({
                        "name": "📍 Location Information",
                        "value": "\n".join(geo_text),
                        "inline": False
                    })

            # Detection time and environment
            fields.append({
                "name": "⏰ Detected At",
                "value": datetime.now().strftime("%A, %B %d, %Y at %H:%M:%S"),
                "inline": False
            })

            fields.append({
                "name": "🐳 Environment",
                "value": "Running in Docker",
                "inline": True
            })

            fields.append({
                "name": "📦 Version",
                "value": f"v{version}",
                "inline": True
            })

            # Build payload
            payload = {
                "username": self.bot_name,
                "embeds": [{
                    "title": f"🌐 WAN IP Monitor Alert",
                    "description": f"**{title}**\n\n{change_info}",
                    "color": color,
                    "fields": fields,
                    "footer": {
                        "text": f"WANwatcher v{version} on {server_name}"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }

            # Only include avatar_url if custom avatar is provided
            # Otherwise Discord uses the webhook's configured avatar
            avatar_url = self._get_avatar_url()
            if avatar_url:
                payload["avatar_url"] = avatar_url

            # Send webhook
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 204:
                logger.info(f"Discord notification sent successfully (Status: {response.status_code})")
                return True
            else:
                logger.error(f"Discord notification failed (Status: {response.status_code}): {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False

    def send_update_notification(self, update_info: Dict[str, str], server_name: str, version: str = "1.4.0") -> bool:
        """Send Discord update notification"""
        try:
            # Extract changelog highlights (first few bullet points)
            changelog = update_info.get('release_body', '')
            changelog_lines = []
            for line in changelog.split('\n')[:15]:  # Check more lines
                line = line.strip()
                if line and (line.startswith('- ') or line.startswith('* ') or line.startswith('• ')):
                    # Clean up markdown list markers
                    cleaned = line.lstrip('-*• ').strip()
                    if cleaned and not cleaned.startswith('#') and len(cleaned) < 100:  # Skip headers and long lines
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
                        "inline": True
                    },
                    {
                        "name": "🎁 Latest Version",
                        "value": f"`v{update_info['latest_version']}`",
                        "inline": True
                    },
                    {
                        "name": "\u200b",  # Empty field for spacing
                        "value": "\u200b",
                        "inline": False
                    },
                    {
                        "name": "📋 What's New",
                        "value": changelog_preview.strip(),
                        "inline": False
                    },
                    {
                        "name": "🔗 Full Changelog",
                        "value": f"[View Release Notes]({update_info['release_url']})",
                        "inline": False
                    },
                    {
                        "name": "💡 How to Update",
                        "value": "```bash\ndocker pull noxied/wanwatcher:latest\ndocker restart wanwatcher\n```",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"Update check for {server_name}"
                },
                "timestamp": datetime.utcnow().isoformat()
            }

            payload = {
                "username": self.bot_name,
                "embeds": [embed]
            }

            # Only include avatar_url if custom avatar is provided
            avatar_url = self._get_avatar_url()
            if avatar_url:
                payload["avatar_url"] = avatar_url

            response = requests.post(self.webhook_url, json=payload, timeout=10)

            if response.status_code == 204:
                logger.info("Discord update notification sent successfully")
                return True
            else:
                logger.error(f"Discord update notification failed (Status: {response.status_code})")
                return False

        except Exception as e:
            logger.error(f"Failed to send Discord update notification: {e}")
            return False


class TelegramNotifier(NotificationProvider):
    """Telegram bot notification provider"""

    def __init__(self, bot_token: str, chat_id: str, parse_mode: str = "HTML"):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.parse_mode = parse_mode
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def send_notification(self, current_ips: Dict[str, Optional[str]],
                         previous_ips: Dict[str, Optional[str]],
                         geo_data: Optional[Dict[str, Any]],
                         is_first_run: bool,
                         server_name: str,
                         version: str = "1.4.0") -> bool:
        """Send Telegram notification"""
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
                ""
            ]

            # IP Change details (if not first run)
            if not is_first_run:
                message_lines.append("<b>📊 Changes Detected:</b>")
                if current_ips.get('ipv4') != previous_ips.get('ipv4'):
                    message_lines.append(f"  • IPv4: <code>{previous_ips.get('ipv4', 'None')}</code> → <code>{current_ips.get('ipv4', 'None')}</code>")
                if current_ips.get('ipv6') != previous_ips.get('ipv6'):
                    message_lines.append(f"  • IPv6: <code>{previous_ips.get('ipv6', 'None')}</code> → <code>{current_ips.get('ipv6', 'None')}</code>")
                message_lines.append("")

            # Current IPs
            if current_ips.get('ipv4'):
                message_lines.append(f"<b>📍 Current IPv4:</b>\n<code>{current_ips['ipv4']}</code>")
                message_lines.append("")

            if current_ips.get('ipv6'):
                message_lines.append(f"<b>📍 Current IPv6:</b>\n<code>{current_ips['ipv6']}</code>")
                message_lines.append("")

            # Geographic information
            if geo_data:
                message_lines.append("<b>📍 Location Information</b>")
                if geo_data.get('city') or geo_data.get('region') or geo_data.get('country'):
                    location = ", ".join(filter(None, [
                        geo_data.get('city'),
                        geo_data.get('region'),
                        geo_data.get('country')
                    ]))
                    message_lines.append(f"🌍 {location}")

                if geo_data.get('org'):
                    message_lines.append(f"🏢 {geo_data['org']}")

                if geo_data.get('timezone'):
                    message_lines.append(f"🕐 {geo_data['timezone']}")

                message_lines.append("")

            # Metadata
            message_lines.extend([
                f"<b>⏰ Detected At:</b> {datetime.now().strftime('%A, %B %d, %Y at %H:%M:%S')}",
                f"<b>🐳 Environment:</b> Running in Docker",
                f"<b>📦 Version:</b> v{version}"
            ])

            message = "\n".join(message_lines)

            # Send message
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": self.parse_mode
            }

            response = requests.post(self.api_url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
                return True
            else:
                logger.error(f"Telegram notification failed (Status: {response.status_code}): {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    def send_update_notification(self, update_info: Dict[str, str], server_name: str, version: str = "1.4.0") -> bool:
        """Send Telegram update notification"""
        try:
            # Extract changelog highlights
            changelog = update_info.get('release_body', '')
            changelog_lines = []
            for line in changelog.split('\n')[:8]:
                line = line.strip()
                if line and (line.startswith('- ') or line.startswith('* ') or line.startswith('• ')):
                    cleaned = line.lstrip('-*• ').strip()
                    if cleaned and not cleaned.startswith('#'):
                        changelog_lines.append(f"  • {cleaned}")

            changelog_preview = '\n'.join(changelog_lines[:5]) if changelog_lines else "See release notes for details"

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
                f"<b>🔗 Full Changelog:</b>",
                f"<a href=\"{update_info['release_url']}\">View Release Notes</a>",
                "",
                "<b>💡 How to Update:</b>",
                "<code>docker pull noxied/wanwatcher:latest</code>",
                "<code>docker restart wanwatcher</code>",
                "",
                f"<i>Update check for {server_name}</i>"
            ]

            message = "\n".join(message_lines)

            # Send message
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": self.parse_mode,
                "disable_web_page_preview": False
            }

            response = requests.post(self.api_url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info("Telegram update notification sent successfully")
                return True
            else:
                logger.error(f"Telegram update notification failed (Status: {response.status_code})")
                return False

        except Exception as e:
            logger.error(f"Failed to send Telegram update notification: {e}")
            return False


class EmailNotifier(NotificationProvider):
    """Email SMTP notification provider"""

    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str,
                 from_addr: str, to_addrs: Union[str, List[str]], use_tls: bool = True, use_ssl: bool = False,
                 subject_prefix: str = "[WANwatcher]"):
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_addr = from_addr
        # Handle both string and list inputs for to_addrs
        if isinstance(to_addrs, list):
            self.to_addrs = to_addrs
        else:
            self.to_addrs = [addr.strip() for addr in to_addrs.split(',')]
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.subject_prefix = subject_prefix

    def _build_html_email(self, current_ips: Dict[str, Optional[str]],
                         previous_ips: Dict[str, Optional[str]],
                         geo_data: Optional[Dict[str, Any]],
                         is_first_run: bool,
                         server_name: str,
                         version: str = "1.4.0") -> str:
        """Build HTML email content with Gmail-compatible inline styles (no <style> tag)"""

        # Determine colors and title
        if is_first_run:
            header_color = "#4CAF50"  # Green
            title = "✅ Initial IP Detection"
            subtitle = f"Monitoring started for {server_name}"
        else:
            header_color = "#FF9800"  # Orange
            title = "🔄 IP Address Changed"

            # Build change details
            changes = []
            if current_ips.get('ipv4') != previous_ips.get('ipv4'):
                changes.append(f"<strong>IPv4:</strong> {previous_ips.get('ipv4', 'None')} → {current_ips.get('ipv4', 'None')}")
            if current_ips.get('ipv6') != previous_ips.get('ipv6'):
                changes.append(f"<strong>IPv6:</strong> {previous_ips.get('ipv6', 'None')} → {current_ips.get('ipv6', 'None')}")

            subtitle = "<br>".join(changes) if changes else "IP information updated"

        # Build HTML with ALL INLINE STYLES (Gmail strips <style> tags)
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #e0e0e0; margin: 0; padding: 10px; background-color: #2c2c2c;">
    <div style="max-width: 600px; margin: 10px auto; background-color: #1e1e1e; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
        <img src="https://raw.githubusercontent.com/noxied/wanwatcher/main/wanwatcher-banner.png" alt="WANwatcher" style="width: 100%; height: auto; display: block;">

        <div style="background: linear-gradient(135deg, {header_color} 0%, #0099CC 100%); color: white; padding: 20px 15px; text-align: center;">
            <h1 style="margin: 0 0 8px 0; font-size: 24px; font-weight: 700; color: white;">🌐 WAN IP Monitor Alert</h1>
            <h2 style="margin: 8px 0 0 0; font-size: 20px; font-weight: 600; color: white;">{title}</h2>
            <p style="margin: 10px 0 0 0; font-size: 15px; opacity: 0.95; color: white;">{subtitle}</p>
        </div>

        <div style="padding: 20px 15px; background-color: #1e1e1e;">
"""

        # Current IPs section
        html += f'<div style="font-size: 17px; font-weight: 700; color: {header_color}; margin: 20px 0 12px 0; padding-bottom: 6px; border-bottom: 2px solid {header_color};">📍 Current IP Addresses</div>'
        html += '<table style="width: 100%; border-collapse: collapse; margin: 15px 0; background-color: #252525; border-radius: 6px;">'

        if current_ips.get('ipv4'):
            html += f"""
            <tr>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">IPv4 Address:</td>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">{current_ips['ipv4']}</td>
            </tr>
"""

        if current_ips.get('ipv6'):
            html += f"""
            <tr>
                <td style="padding: 12px 15px; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">IPv6 Address:</td>
                <td style="padding: 12px 15px; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">{current_ips['ipv6']}</td>
            </tr>
"""

        html += '</table>'

        # Geographic information
        if geo_data:
            html += f'<div style="font-size: 17px; font-weight: 700; color: {header_color}; margin: 20px 0 12px 0; padding-bottom: 6px; border-bottom: 2px solid {header_color};">📍 Location Information</div>'
            html += '<table style="width: 100%; border-collapse: collapse; margin: 15px 0; background-color: #252525; border-radius: 6px;">'

            if geo_data.get('city') or geo_data.get('region') or geo_data.get('country'):
                location = ", ".join(filter(None, [
                    geo_data.get('city'),
                    geo_data.get('region'),
                    geo_data.get('country')
                ]))
                html += f"""
            <tr>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">Location:</td>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">🌍 {location}</td>
            </tr>
"""

            if geo_data.get('org'):
                html += f"""
            <tr>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">ISP / Organization:</td>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">🏢 {geo_data['org']}</td>
            </tr>
"""

            if geo_data.get('timezone'):
                html += f"""
            <tr>
                <td style="padding: 12px 15px; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">Timezone:</td>
                <td style="padding: 12px 15px; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">🕐 {geo_data['timezone']}</td>
            </tr>
"""

            html += '</table>'

        # Metadata
        html += f'<div style="font-size: 17px; font-weight: 700; color: {header_color}; margin: 20px 0 12px 0; padding-bottom: 6px; border-bottom: 2px solid {header_color};">ℹ️ Detection Details</div>'
        html += f"""
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0; background-color: #252525; border-radius: 6px;">
            <tr>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">Server Name:</td>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">{server_name}</td>
            </tr>
            <tr>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">Detected At:</td>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">{datetime.now().strftime('%A, %B %d, %Y at %H:%M:%S')}</td>
            </tr>
            <tr>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">Environment:</td>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">🐳 Running in Docker</td>
            </tr>
            <tr>
                <td style="padding: 12px 15px; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">Version:</td>
                <td style="padding: 12px 15px; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">📦 v{version}</td>
            </tr>
        </table>

        </div>

        <div style="background: linear-gradient(135deg, #1a5f7a 0%, #16213e 100%); padding: 20px 15px; text-align: center; font-size: 13px; color: #e0e0e0;">
            <p style="margin: 0 0 10px 0;">
                <span style="display: inline-block; padding: 5px 10px; background-color: rgba(255,255,255,0.15); border-radius: 5px; font-size: 12px; color: white; margin: 0 4px;">🐳 WANwatcher v{version}</span>
                <span style="display: inline-block; padding: 5px 10px; background-color: rgba(255,255,255,0.15); border-radius: 5px; font-size: 12px; color: white; margin: 0 4px;">📍 {server_name}</span>
            </p>
            <p style="margin: 0; font-size: 14px; color: #e0e0e0;">
                🌐 Automated WAN IP Monitoring System
            </p>
            <p style="margin: 8px 0 0 0; font-size: 11px; opacity: 0.8; color: #e0e0e0;">
                Multi-Platform Notifications: Discord • Telegram • Email
            </p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _build_text_email(self, current_ips: Dict[str, Optional[str]],
                         previous_ips: Dict[str, Optional[str]],
                         geo_data: Optional[Dict[str, Any]],
                         is_first_run: bool,
                         server_name: str,
                         version: str = "1.4.0") -> str:
        """Build plain text email content"""

        lines = [
            "=" * 60,
            "WAN IP MONITOR ALERT",
            "=" * 60,
            ""
        ]

        if is_first_run:
            lines.extend([
                "✅ Initial IP Detection",
                f"Monitoring started for {server_name}",
                ""
            ])
        else:
            lines.extend([
                "🔄 IP Address Changed",
                ""
            ])

            if current_ips.get('ipv4') != previous_ips.get('ipv4'):
                lines.append(f"IPv4: {previous_ips.get('ipv4', 'None')} → {current_ips.get('ipv4', 'None')}")
            if current_ips.get('ipv6') != previous_ips.get('ipv6'):
                lines.append(f"IPv6: {previous_ips.get('ipv6', 'None')} → {current_ips.get('ipv6', 'None')}")

            lines.append("")

        # Current IPs
        lines.append("CURRENT IP ADDRESSES:")
        lines.append("-" * 60)
        if current_ips.get('ipv4'):
            lines.append(f"IPv4: {current_ips['ipv4']}")
        if current_ips.get('ipv6'):
            lines.append(f"IPv6: {current_ips['ipv6']}")
        lines.append("")

        # Geographic info
        if geo_data:
            lines.append("LOCATION INFORMATION:")
            lines.append("-" * 60)
            if geo_data.get('city') or geo_data.get('region') or geo_data.get('country'):
                location = ", ".join(filter(None, [
                    geo_data.get('city'),
                    geo_data.get('region'),
                    geo_data.get('country')
                ]))
                lines.append(f"Location: {location}")
            if geo_data.get('org'):
                lines.append(f"ISP: {geo_data['org']}")
            if geo_data.get('timezone'):
                lines.append(f"Timezone: {geo_data['timezone']}")
            lines.append("")

        # Metadata
        lines.extend([
            "DETECTION DETAILS:",
            "-" * 60,
            f"Server: {server_name}",
            f"Detected: {datetime.now().strftime('%A, %B %d, %Y at %H:%M:%S')}",
            f"Environment: Docker",
            f"Version: v{version}",
            "",
            "=" * 60,
            f"WANwatcher v{version} on {server_name}",
            "=" * 60
        ])

        return "\n".join(lines)

    def send_notification(self, current_ips: Dict[str, Optional[str]],
                         previous_ips: Dict[str, Optional[str]],
                         geo_data: Optional[Dict[str, Any]],
                         is_first_run: bool,
                         server_name: str,
                         version: str = "1.4.0") -> bool:
        """Send email notification via SMTP"""
        try:
            # Build subject
            if is_first_run:
                subject = f"{self.subject_prefix} Initial IP Detection - {server_name}"
            else:
                subject = f"{self.subject_prefix} IP Address Changed - {server_name}"

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_addr
            msg['To'] = ', '.join(self.to_addrs)
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

            # Add plain text version
            text_content = self._build_text_email(current_ips, previous_ips, geo_data, is_first_run, server_name, version)
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

            # Add HTML version
            html_content = self._build_html_email(current_ips, previous_ips, geo_data, is_first_run, server_name, version)
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # Send email
            if self.use_ssl:
                # SSL connection (port 465)
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                # TLS connection (port 587) or plain (port 25)
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.ehlo()
                    if self.use_tls:
                        server.starttls()
                        server.ehlo()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

            logger.info(f"Email notification sent successfully to {', '.join(self.to_addrs)}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    def send_update_notification(self, update_info: Dict[str, str], server_name: str, version: str = "1.4.0") -> bool:
        """Send email update notification"""
        try:
            subject = f"{self.subject_prefix} Update Available: v{update_info['latest_version']}"

            # Extract changelog highlights
            changelog = update_info.get('release_body', '')
            changelog_lines = []
            for line in changelog.split('\n')[:8]:
                line = line.strip()
                if line and (line.startswith('- ') or line.startswith('* ') or line.startswith('• ')):
                    cleaned = line.lstrip('-*• ').strip()
                    if cleaned and not cleaned.startswith('#'):
                        changelog_lines.append(f"  • {cleaned}")

            changelog_preview = '\n'.join(changelog_lines[:5]) if changelog_lines else "See release notes for details"

            # Plain text version
            text_content = f"""
WANwatcher Update Available!

Current Version: v{update_info['current_version']}
Latest Version: v{update_info['latest_version']}

What's New:
{changelog_preview}

View Full Changelog:
{update_info['release_url']}

How to Update:
docker pull noxied/wanwatcher:latest
docker restart wanwatcher

---
Update check for {server_name}
WANwatcher Update Notification
"""

            # HTML version (Dark theme matching IP detection notification)
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #e0e0e0; margin: 0; padding: 10px; background-color: #2c2c2c; }}
        .container {{ max-width: 600px; margin: 10px auto; background-color: #1e1e1e; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
        .banner {{ width: 100%; height: auto; display: block; }}
        .header {{ background: linear-gradient(135deg, #00D9FF 0%, #0099CC 100%); color: white; padding: 20px 15px; text-align: center; }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 24px; font-weight: 700; color: white; }}
        .header p {{ margin: 10px 0 0 0; font-size: 15px; opacity: 0.95; color: white; }}
        .content {{ padding: 20px 15px; background-color: #1e1e1e; }}
        .section-title {{ font-size: 17px; font-weight: 700; color: #00D9FF; margin: 20px 0 12px 0; padding-bottom: 6px; border-bottom: 2px solid #00D9FF; }}
        .version-box {{ background-color: #252525; border-left: 4px solid #00D9FF; padding: 15px; margin: 15px 0; border-radius: 6px; }}
        .version-box strong {{ color: #4CAF50; font-size: 15px; }}
        .version-text {{ color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; }}
        .changelog {{ background-color: #252525; padding: 15px; border-radius: 6px; margin: 15px 0; border: 1px solid #333; }}
        .changelog h3 {{ margin-top: 0; color: #00D9FF; font-size: 16px; }}
        .changelog-content {{ color: #e0e0e0; font-family: Arial, sans-serif; white-space: pre-wrap; font-size: 14px; line-height: 1.8; }}
        .button {{ display: inline-block; background: linear-gradient(135deg, #00D9FF 0%, #0099CC 100%); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 15px 0; font-weight: 600; box-shadow: 0 2px 8px rgba(0,217,255,0.3); }}
        .code-section {{ margin: 15px 0; }}
        .code-section h3 {{ color: #e0e0e0; font-size: 16px; margin-bottom: 10px; }}
        .code {{ background-color: #2d2d2d; color: #00ff00; padding: 15px; border-radius: 6px; font-family: 'Courier New', monospace; margin: 10px 0; font-size: 13px; border: 1px solid #404040; }}
        .footer {{ background: linear-gradient(135deg, #1a5f7a 0%, #16213e 100%); padding: 20px 15px; text-align: center; font-size: 13px; color: #e0e0e0; }}
        .badge {{ display: inline-block; padding: 5px 10px; background-color: rgba(255,255,255,0.15); border-radius: 5px; font-size: 12px; color: white; margin: 0 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <img src="https://raw.githubusercontent.com/noxied/wanwatcher/main/wanwatcher-banner.png" alt="WANwatcher" class="banner">
        <div class="header">
            <h1>🆕 WANwatcher Update Available!</h1>
            <p>A new version is ready to install</p>
        </div>
        <div class="content">
            <div class="section-title">📦 Version Information</div>
            <div class="version-box">
                <strong>Current Version:</strong> <span class="version-text">v{update_info['current_version']}</span><br><br>
                <strong>Latest Version:</strong> <span class="version-text">v{update_info['latest_version']}</span>
            </div>

            <div class="section-title">📋 What's New</div>
            <div class="changelog">
                <div class="changelog-content">{changelog_preview if changelog_preview.strip() else 'See release notes for details'}</div>
            </div>

            <center>
                <a href="{update_info['release_url']}" class="button">🔗 View Full Changelog</a>
            </center>

            <div class="section-title">💡 How to Update</div>
            <div class="code">
docker pull noxied/wanwatcher:latest<br>
docker restart wanwatcher
            </div>
        </div>
        <div class="footer">
            <p style="margin: 0 0 10px 0;">
                <span class="badge">🐳 WANwatcher v{version}</span>
                <span class="badge">📍 {server_name}</span>
            </p>
            <p style="margin: 0; font-size: 14px; color: #e0e0e0;">
                🌐 Automated WAN IP Monitoring System
            </p>
            <p style="margin: 8px 0 0 0; font-size: 11px; opacity: 0.8; color: #e0e0e0;">
                Multi-Platform Notifications: Discord • Telegram • Email
            </p>
        </div>
    </div>
</body>
</html>
"""

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_addr
            msg['To'] = ', '.join(self.to_addrs)
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # Send email
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.ehlo()
                    if self.use_tls:
                        server.starttls()
                        server.ehlo()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

            logger.info(f"Email update notification sent successfully to {', '.join(self.to_addrs)}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email update notification: {e}")
            return False


class NotificationManager:
    """Manages multiple notification providers"""

    def __init__(self):
        self.providers = []

    def add_provider(self, provider: NotificationProvider):
        """Add a notification provider"""
        self.providers.append(provider)

    def send_to_all(self, current_ips: Dict[str, Optional[str]],
                   previous_ips: Dict[str, Optional[str]],
                   geo_data: Optional[Dict[str, Any]],
                   is_first_run: bool,
                   server_name: str,
                   version: str = "1.4.0") -> Dict[str, bool]:
        """Send notification to all configured providers with retry logic"""
        results = {}

        for i, provider in enumerate(self.providers):
            provider_name = provider.__class__.__name__
            logger.info(f"Sending notification via {provider_name}...")

            # Create a lambda that wraps the provider call
            def send_func():
                return provider.send_notification(
                    current_ips, previous_ips, geo_data, is_first_run, server_name, version
                )

            # Try sending with retry logic
            success = retry_with_backoff(send_func, max_retries=3, base_delay=2.0)
            results[provider_name] = success

            if success:
                logger.info(f"{provider_name} notification sent successfully")
            else:
                logger.error(f"{provider_name} notification failed after all retries")

        return results

    def notify_update(self, update_info: Dict[str, str], server_name: str, version: str = "1.4.0") -> Dict[str, bool]:
        """Send update notification to all configured providers with retry logic"""
        results = {}

        for provider in self.providers:
            provider_name = provider.__class__.__name__
            logger.info(f"Sending update notification via {provider_name}...")

            # Create a lambda that wraps the provider call
            def send_func():
                return provider.send_update_notification(update_info, server_name, version)

            # Try sending with retry logic
            success = retry_with_backoff(send_func, max_retries=3, base_delay=2.0)
            results[provider_name] = success

            if success:
                logger.info(f"{provider_name} update notification sent successfully")
            else:
                logger.error(f"{provider_name} update notification failed after all retries")

        return results

    # Alias for backward compatibility
    def notify_all(self, current_ips, previous_ips, geo_data, is_first_run, server_name, version="1.4.0"):
        """Alias for send_to_all"""
        return self.send_to_all(current_ips, previous_ips, geo_data, is_first_run, server_name, version)

    def notify_error(self, error_msg: str, server_name: str):
        """Notify about errors (placeholder - can be implemented if needed)"""
        logger.error(f"Error notification: {error_msg}")

