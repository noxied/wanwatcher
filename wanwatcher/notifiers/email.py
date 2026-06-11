"""Email SMTP notification provider."""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Union

from wanwatcher.notifiers.base import NotificationProvider

logger = logging.getLogger(__name__)


class EmailNotifier(NotificationProvider):
    """Email SMTP notification provider."""

    name = "email"

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_addr: str,
        to_addrs: Union[str, List[str]],
        use_tls: bool = True,
        use_ssl: bool = False,
        subject_prefix: str = "[WANwatcher]",
    ):
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_addr = from_addr
        # Handle both string and list inputs for to_addrs
        if isinstance(to_addrs, list):
            self.to_addrs = to_addrs
        else:
            self.to_addrs = [addr.strip() for addr in to_addrs.split(",")]
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.subject_prefix = subject_prefix

    def _send_message(self, msg: MIMEMultipart) -> None:
        """Deliver a prepared message over SMTP (SSL, STARTTLS, or plain)."""
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

    def _build_message(self, subject: str, text: str, html: str) -> MIMEMultipart:
        """Build a multipart/alternative message with text and HTML parts."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
        msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        return msg

    def _build_html_email(
        self,
        current_ips: Dict[str, Optional[str]],
        previous_ips: Dict[str, Optional[str]],
        geo_data: Optional[Dict[str, Any]],
        is_first_run: bool,
        server_name: str,
        version: str = "",
    ) -> str:
        """Build HTML email content with Gmail-compatible inline styles."""

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
            if current_ips.get("ipv4") != previous_ips.get("ipv4"):
                changes.append(
                    f"<strong>IPv4:</strong> {previous_ips.get('ipv4', 'None')} → "
                    f"{current_ips.get('ipv4', 'None')}"
                )
            if current_ips.get("ipv6") != previous_ips.get("ipv6"):
                changes.append(
                    f"<strong>IPv6:</strong> {previous_ips.get('ipv6', 'None')} → "
                    f"{current_ips.get('ipv6', 'None')}"
                )

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

        if current_ips.get("ipv4"):
            html += f"""
            <tr>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">IPv4 Address:</td>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">{current_ips['ipv4']}</td>
            </tr>
"""

        if current_ips.get("ipv6"):
            html += f"""
            <tr>
                <td style="padding: 12px 15px; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">IPv6 Address:</td>
                <td style="padding: 12px 15px; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">{current_ips['ipv6']}</td>
            </tr>
"""

        html += "</table>"

        # Geographic information
        if geo_data:
            html += f'<div style="font-size: 17px; font-weight: 700; color: {header_color}; margin: 20px 0 12px 0; padding-bottom: 6px; border-bottom: 2px solid {header_color};">📍 Location Information</div>'
            html += '<table style="width: 100%; border-collapse: collapse; margin: 15px 0; background-color: #252525; border-radius: 6px;">'

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
                html += f"""
            <tr>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">Location:</td>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">🌍 {location}</td>
            </tr>
"""

            if geo_data.get("org"):
                html += f"""
            <tr>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">ISP / Organization:</td>
                <td style="padding: 12px 15px; border-bottom: 1px solid #333; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">🏢 {geo_data['org']}</td>
            </tr>
"""

            if geo_data.get("timezone"):
                html += f"""
            <tr>
                <td style="padding: 12px 15px; font-weight: 600; color: #4CAF50; width: 40%; background-color: #2a2a2a;">Timezone:</td>
                <td style="padding: 12px 15px; color: #e0e0e0; font-family: 'Courier New', monospace; font-weight: 500; background-color: #252525;">🕐 {geo_data['timezone']}</td>
            </tr>
"""

            html += "</table>"

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

    def _build_text_email(
        self,
        current_ips: Dict[str, Optional[str]],
        previous_ips: Dict[str, Optional[str]],
        geo_data: Optional[Dict[str, Any]],
        is_first_run: bool,
        server_name: str,
        version: str = "",
    ) -> str:
        """Build plain text email content."""

        lines = ["=" * 60, "WAN IP MONITOR ALERT", "=" * 60, ""]

        if is_first_run:
            lines.extend(
                ["✅ Initial IP Detection", f"Monitoring started for {server_name}", ""]
            )
        else:
            lines.extend(["🔄 IP Address Changed", ""])

            if current_ips.get("ipv4") != previous_ips.get("ipv4"):
                lines.append(
                    f"IPv4: {previous_ips.get('ipv4', 'None')} → "
                    f"{current_ips.get('ipv4', 'None')}"
                )
            if current_ips.get("ipv6") != previous_ips.get("ipv6"):
                lines.append(
                    f"IPv6: {previous_ips.get('ipv6', 'None')} → "
                    f"{current_ips.get('ipv6', 'None')}"
                )

            lines.append("")

        # Current IPs
        lines.append("CURRENT IP ADDRESSES:")
        lines.append("-" * 60)
        if current_ips.get("ipv4"):
            lines.append(f"IPv4: {current_ips['ipv4']}")
        if current_ips.get("ipv6"):
            lines.append(f"IPv6: {current_ips['ipv6']}")
        lines.append("")

        # Geographic info
        if geo_data:
            lines.append("LOCATION INFORMATION:")
            lines.append("-" * 60)
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
                lines.append(f"Location: {location}")
            if geo_data.get("org"):
                lines.append(f"ISP: {geo_data['org']}")
            if geo_data.get("timezone"):
                lines.append(f"Timezone: {geo_data['timezone']}")
            lines.append("")

        # Metadata
        lines.extend(
            [
                "DETECTION DETAILS:",
                "-" * 60,
                f"Server: {server_name}",
                f"Detected: {datetime.now().strftime('%A, %B %d, %Y at %H:%M:%S')}",
                "Environment: Docker",
                f"Version: v{version}",
                "",
                "=" * 60,
                f"WANwatcher v{version} on {server_name}",
                "=" * 60,
            ]
        )

        return "\n".join(lines)

    def send_notification(
        self,
        current_ips: Dict[str, Optional[str]],
        previous_ips: Dict[str, Optional[str]],
        geo_data: Optional[Dict[str, Any]],
        is_first_run: bool,
        server_name: str,
        version: str = "",
    ) -> bool:
        """Send email notification via SMTP."""
        try:
            # Build subject
            if is_first_run:
                subject = f"{self.subject_prefix} Initial IP Detection - {server_name}"
            else:
                subject = f"{self.subject_prefix} IP Address Changed - {server_name}"

            text_content = self._build_text_email(
                current_ips, previous_ips, geo_data, is_first_run, server_name, version
            )
            html_content = self._build_html_email(
                current_ips, previous_ips, geo_data, is_first_run, server_name, version
            )

            msg = self._build_message(subject, text_content, html_content)
            self._send_message(msg)

            logger.info(
                "Email notification sent successfully to %s", ", ".join(self.to_addrs)
            )
            return True

        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error("Failed to send email notification: %s", exc)
            return False

    def send_update_notification(
        self, update_info: Dict[str, str], server_name: str, version: str = ""
    ) -> bool:
        """Send email update notification."""
        try:
            subject = (
                f"{self.subject_prefix} Update Available: "
                f"v{update_info['latest_version']}"
            )

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

            msg = self._build_message(subject, text_content, html_content)
            self._send_message(msg)

            logger.info(
                "Email update notification sent successfully to %s",
                ", ".join(self.to_addrs),
            )
            return True

        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error("Failed to send email update notification: %s", exc)
            return False

    def send_event(
        self,
        title: str,
        message: str,
        server_name: str,
        severity: str = "info",
    ) -> bool:
        """Send a simple event email with plain text and minimal HTML body."""
        try:
            subject = f"{self.subject_prefix} {title}"

            text_content = "\n".join([title, "", message, "", f"-- {server_name}"])

            html_content = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <h2 style="margin: 0 0 12px 0;">{title}</h2>
    <p style="margin: 0 0 16px 0; white-space: pre-wrap;">{message}</p>
    <p style="margin: 0; color: #666;"><i>{server_name}</i></p>
</body>
</html>
"""

            msg = self._build_message(subject, text_content, html_content)
            self._send_message(msg)

            logger.info(
                "Email event notification sent successfully to %s",
                ", ".join(self.to_addrs),
            )
            return True

        except Exception as exc:  # noqa: BLE001 - notification errors must not crash
            logger.error("Failed to send email event notification: %s", exc)
            return False
