"""
WANwatcher Notification Providers v1.3.0
Supports Discord, Telegram, and Email notifications
"""

import requests
import logging
import json
import base64
import os
from typing import Optional, Dict, Any
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class NotificationProvider:
    """Base class for notification providers"""
    
    def send_notification(self, current_ips: Dict[str, Optional[str]], 
                         previous_ips: Dict[str, Optional[str]], 
                         geo_data: Optional[Dict[str, Any]], 
                         is_first_run: bool,
                         server_name: str) -> bool:
        """Send notification - to be implemented by subclasses"""
        raise NotImplementedError
    
    def send_update_notification(self, update_info: Dict[str, str], server_name: str) -> bool:
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
        """Get avatar URL - custom or default embedded"""
        if self.avatar_url:
            return self.avatar_url
        
        # Try to use embedded avatar as data URL
        if os.path.exists(self.default_avatar_path):
            try:
                with open(self.default_avatar_path, 'rb') as f:
                    img_data = f.read()
                    b64_data = base64.b64encode(img_data).decode('utf-8')
                    return f"data:image/png;base64,{b64_data}"
            except Exception as e:
                logger.warning(f"Failed to load default avatar: {e}")
        
        return ""  # Discord will use default webhook avatar
        
    def send_notification(self, current_ips: Dict[str, Optional[str]], 
                         previous_ips: Dict[str, Optional[str]], 
                         geo_data: Optional[Dict[str, Any]], 
                         is_first_run: bool,
                         server_name: str) -> bool:
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
                "value": "v1.3.0",
                "inline": True
            })
            
            # Build payload
            payload = {
                "username": self.bot_name,
                "avatar_url": self._get_avatar_url(),
                "embeds": [{
                    "title": f"🌐 WAN IP Monitor Alert",
                    "description": f"**{title}**\n\n{change_info}",
                    "color": color,
                    "fields": fields,
                    "footer": {
                        "text": f"WANwatcher v1.3.0 on {server_name}"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            
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
    
    def send_update_notification(self, update_info: Dict[str, str], server_name: str) -> bool:
        """Send Discord update notification"""
        try:
            # Extract changelog highlights (first few bullet points)
            changelog = update_info.get('release_body', '')
            changelog_lines = []
            for line in changelog.split('\n')[:8]:  # First 8 lines
                line = line.strip()
                if line and (line.startswith('- ') or line.startswith('* ') or line.startswith('• ')):
                    # Clean up markdown list markers
                    cleaned = line.lstrip('-*• ').strip()
                    if cleaned and not cleaned.startswith('#'):  # Skip headers
                        changelog_lines.append(f"• {cleaned}")
            
            changelog_preview = '\n'.join(changelog_lines[:5]) if changelog_lines else "See release notes for details"
            
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
                        "value": changelog_preview,
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
                "avatar_url": self._get_avatar_url(),
                "embeds": [embed]
            }
            
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
                         server_name: str) -> bool:
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
                f"<b>📦 Version:</b> v1.3.0"
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
    
    def send_update_notification(self, update_info: Dict[str, str], server_name: str) -> bool:
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
                 from_addr: str, to_addrs: str, use_tls: bool = True, use_ssl: bool = False,
                 subject_prefix: str = "[WANwatcher]"):
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_addr = from_addr
        self.to_addrs = [addr.strip() for addr in to_addrs.split(',')]
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.subject_prefix = subject_prefix
        
    def _build_html_email(self, current_ips: Dict[str, Optional[str]], 
                         previous_ips: Dict[str, Optional[str]], 
                         geo_data: Optional[Dict[str, Any]], 
                         is_first_run: bool,
                         server_name: str) -> str:
        """Build HTML email content"""
        
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
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 600px;
            margin: 20px auto;
            background: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{
            background: {header_color};
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .header p {{
            margin: 0;
            font-size: 14px;
            opacity: 0.95;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .info-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .info-table td:first-child {{
            font-weight: 600;
            color: #555;
            width: 35%;
        }}
        .info-table td:last-child {{
            color: #333;
            font-family: 'Courier New', monospace;
        }}
        .info-table tr:last-child td {{
            border-bottom: none;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            color: {header_color};
            margin: 25px 0 10px 0;
            padding-bottom: 5px;
            border-bottom: 2px solid {header_color};
        }}
        .footer {{
            background: #f9f9f9;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
            border-top: 1px solid #e0e0e0;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            background: #f0f0f0;
            border-radius: 4px;
            font-size: 12px;
            color: #666;
            margin: 0 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 WAN IP Monitor Alert</h1>
            <h2 style="margin: 10px 0 0 0; font-size: 20px; font-weight: 500;">{title}</h2>
            <p style="margin-top: 10px;">{subtitle}</p>
        </div>
        
        <div class="content">
"""
        
        # Current IPs section
        html += '<div class="section-title">📍 Current IP Addresses</div>'
        html += '<table class="info-table">'
        
        if current_ips.get('ipv4'):
            html += f"""
            <tr>
                <td>IPv4 Address:</td>
                <td>{current_ips['ipv4']}</td>
            </tr>
"""
        
        if current_ips.get('ipv6'):
            html += f"""
            <tr>
                <td>IPv6 Address:</td>
                <td>{current_ips['ipv6']}</td>
            </tr>
"""
        
        html += '</table>'
        
        # Geographic information
        if geo_data:
            html += '<div class="section-title">📍 Location Information</div>'
            html += '<table class="info-table">'
            
            if geo_data.get('city') or geo_data.get('region') or geo_data.get('country'):
                location = ", ".join(filter(None, [
                    geo_data.get('city'),
                    geo_data.get('region'),
                    geo_data.get('country')
                ]))
                html += f"""
            <tr>
                <td>Location:</td>
                <td>🌍 {location}</td>
            </tr>
"""
            
            if geo_data.get('org'):
                html += f"""
            <tr>
                <td>ISP / Organization:</td>
                <td>🏢 {geo_data['org']}</td>
            </tr>
"""
            
            if geo_data.get('timezone'):
                html += f"""
            <tr>
                <td>Timezone:</td>
                <td>🕐 {geo_data['timezone']}</td>
            </tr>
"""
            
            html += '</table>'
        
        # Metadata
        html += '<div class="section-title">ℹ️ Detection Details</div>'
        html += f"""
        <table class="info-table">
            <tr>
                <td>Server Name:</td>
                <td>{server_name}</td>
            </tr>
            <tr>
                <td>Detected At:</td>
                <td>{datetime.now().strftime('%A, %B %d, %Y at %H:%M:%S')}</td>
            </tr>
            <tr>
                <td>Environment:</td>
                <td>🐳 Running in Docker</td>
            </tr>
            <tr>
                <td>Version:</td>
                <td>📦 v1.3.0</td>
            </tr>
        </table>
        
        </div>
        
        <div class="footer">
            <p>
                <span class="badge">WANwatcher v1.3.0</span>
                <span class="badge">{server_name}</span>
            </p>
            <p style="margin-top: 10px; color: #999;">
                Automated WAN IP monitoring system
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
                         server_name: str) -> str:
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
            f"Version: v1.3.0",
            "",
            "=" * 60,
            f"WANwatcher v1.3.0 on {server_name}",
            "=" * 60
        ])
        
        return "\n".join(lines)
        
    def send_notification(self, current_ips: Dict[str, Optional[str]], 
                         previous_ips: Dict[str, Optional[str]], 
                         geo_data: Optional[Dict[str, Any]], 
                         is_first_run: bool,
                         server_name: str) -> bool:
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
            text_content = self._build_text_email(current_ips, previous_ips, geo_data, is_first_run, server_name)
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            
            # Add HTML version
            html_content = self._build_html_email(current_ips, previous_ips, geo_data, is_first_run, server_name)
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
    
    def send_update_notification(self, update_info: Dict[str, str], server_name: str) -> bool:
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
            
            # HTML version
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 20px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #00D9FF 0%, #0099CC 100%); color: white; padding: 30px 20px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ padding: 30px 20px; }}
        .version-box {{ background: #f5f5f5; border-left: 4px solid #00D9FF; padding: 15px; margin: 20px 0; }}
        .version-box strong {{ color: #00D9FF; }}
        .changelog {{ background: #fafafa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .changelog h3 {{ margin-top: 0; color: #00D9FF; }}
        .button {{ display: inline-block; background: #00D9FF; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .code {{ background: #2d2d2d; color: #f8f8f8; padding: 15px; border-radius: 5px; font-family: monospace; margin: 10px 0; }}
        .footer {{ background: #f9f9f9; padding: 20px; text-align: center; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🆕 WANwatcher Update Available!</h1>
        </div>
        <div class="content">
            <div class="version-box">
                <strong>Current Version:</strong> v{update_info['current_version']}<br>
                <strong>Latest Version:</strong> v{update_info['latest_version']}
            </div>
            
            <div class="changelog">
                <h3>📋 What's New</h3>
                <pre style="white-space: pre-wrap; font-family: Arial;">{changelog_preview}</pre>
            </div>
            
            <center>
                <a href="{update_info['release_url']}" class="button">View Full Changelog</a>
            </center>
            
            <h3>💡 How to Update</h3>
            <div class="code">
docker pull noxied/wanwatcher:latest<br>
docker restart wanwatcher
            </div>
        </div>
        <div class="footer">
            Update check for {server_name}<br>
            WANwatcher Update Notification
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
                   server_name: str) -> Dict[str, bool]:
        """Send notification to all configured providers"""
        results = {}
        
        for i, provider in enumerate(self.providers):
            provider_name = provider.__class__.__name__
            try:
                success = provider.send_notification(
                    current_ips, previous_ips, geo_data, is_first_run, server_name
                )
                results[provider_name] = success
            except Exception as e:
                logger.error(f"Provider {provider_name} failed: {e}")
                results[provider_name] = False
        
        return results
    
    def notify_update(self, update_info: Dict[str, str], server_name: str) -> Dict[str, bool]:
        """Send update notification to all configured providers"""
        results = {}
        
        for provider in self.providers:
            provider_name = provider.__class__.__name__
            try:
                success = provider.send_update_notification(update_info, server_name)
                results[provider_name] = success
            except Exception as e:
                logger.error(f"Provider {provider_name} update notification failed: {e}")
                results[provider_name] = False
        
        return results
    
    # Alias for backward compatibility
    def notify_all(self, current_ips, previous_ips, geo_data, is_first_run, server_name):
        """Alias for send_to_all"""
        return self.send_to_all(current_ips, previous_ips, geo_data, is_first_run, server_name)
    
    def notify_error(self, error_msg: str, server_name: str):
        """Notify about errors (placeholder - can be implemented if needed)"""
        logger.error(f"Error notification: {error_msg}")

