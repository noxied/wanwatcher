#!/usr/bin/env python3
"""
WANwatcher Notification Providers
Supports multiple notification platforms: Discord, Telegram, etc.

Version: 1.2.0
"""

import requests
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional
from datetime import datetime


# Version
VERSION = "1.2.0"


class NotificationProvider(ABC):
    """Abstract base class for notification providers"""
    
    @abstractmethod
    def send_notification(self, 
                         current_ips: Dict[str, Optional[str]], 
                         previous_ips: Dict[str, Optional[str]],
                         geo_data: Optional[Dict],
                         is_first_run: bool,
                         server_name: str) -> bool:
        """
        Send notification about IP change
        
        Args:
            current_ips: Dict with 'ipv4' and 'ipv6' keys
            previous_ips: Dict with 'ipv4' and 'ipv6' keys
            geo_data: Optional geographic information dict
            is_first_run: Boolean indicating if this is the first run
            server_name: Name of the server for identification
            
        Returns:
            bool: True if notification sent successfully
        """
        pass
    
    @abstractmethod
    def send_error_notification(self, error_message: str, server_name: str) -> bool:
        """Send error notification"""
        pass


class DiscordNotifier(NotificationProvider):
    """Discord webhook notification provider"""
    
    def __init__(self, webhook_url: str, bot_name: str):
        """
        Initialize Discord notifier
        
        Args:
            webhook_url: Discord webhook URL
            bot_name: Display name for the bot
        """
        self.webhook_url = webhook_url
        self.bot_name = bot_name
        logging.info(f"Discord notifier initialized: {bot_name}")
    
    def send_notification(self, 
                         current_ips: Dict[str, Optional[str]], 
                         previous_ips: Dict[str, Optional[str]],
                         geo_data: Optional[Dict],
                         is_first_run: bool,
                         server_name: str) -> bool:
        """Send notification via Discord webhook"""
        
        try:
            # Determine if anything changed
            ipv4_changed = current_ips.get('ipv4') != previous_ips.get('ipv4')
            ipv6_changed = current_ips.get('ipv6') != previous_ips.get('ipv6')
            
            # Build title and description
            if is_first_run:
                title = "🟢 Initial IP Detection"
                description = f"Monitoring started for **{server_name}**"
                color = 3066993  # Green
            elif ipv4_changed and ipv6_changed:
                title = "🔄 Both IP Addresses Changed"
                description = f"IPv4 and IPv6 for **{server_name}** have been updated"
                color = 15844367  # Gold/Orange
            elif ipv4_changed:
                title = "🔄 IPv4 Address Changed"
                description = f"IPv4 for **{server_name}** has been updated"
                color = 15844367  # Gold/Orange
            elif ipv6_changed:
                title = "🔄 IPv6 Address Changed"
                description = f"IPv6 for **{server_name}** has been updated"
                color = 15844367  # Gold/Orange
            else:
                title = "✅ IP Status Update"
                description = f"IP addresses confirmed for **{server_name}**"
                color = 3066993  # Green
            
            # Build fields
            fields = []
            
            # IPv4 section
            if current_ips.get('ipv4'):
                fields.append({
                    "name": "📍 Current IPv4",
                    "value": f"`{current_ips['ipv4']}`",
                    "inline": True
                })
                if previous_ips.get('ipv4') and ipv4_changed and not is_first_run:
                    fields.append({
                        "name": "📌 Previous IPv4",
                        "value": f"`{previous_ips['ipv4']}`",
                        "inline": True
                    })
                    # Add empty field for proper 3-column layout
                    fields.append({"name": "\u200b", "value": "\u200b", "inline": True})
            
            # IPv6 section
            if current_ips.get('ipv6'):
                fields.append({
                    "name": "📍 Current IPv6",
                    "value": f"`{current_ips['ipv6']}`",
                    "inline": False
                })
                if previous_ips.get('ipv6') and ipv6_changed and not is_first_run:
                    fields.append({
                        "name": "📌 Previous IPv6",
                        "value": f"`{previous_ips['ipv6']}`",
                        "inline": False
                    })
            elif current_ips.get('ipv4'):
                fields.append({
                    "name": "ℹ️ IPv6 Status",
                    "value": "Not available or not configured",
                    "inline": False
                })
            
            # Spacer before geo data
            fields.append({"name": "\u200b", "value": "\u200b", "inline": False})
            
            # Geographic information
            if geo_data:
                geo_text = f"🌍 {geo_data.get('city', 'Unknown')}, {geo_data.get('region', '')}, {geo_data.get('country', 'Unknown')}\n"
                geo_text += f"🏢 {geo_data.get('org', 'Unknown ISP')}\n"
                geo_text += f"🕐 {geo_data.get('timezone', 'Unknown')}"
                fields.append({
                    "name": "📍 Location Information",
                    "value": geo_text,
                    "inline": False
                })
            
            # Timestamp
            local_timestamp = int(datetime.now().timestamp())
            fields.append({
                "name": "⏰ Detected At",
                "value": f"<t:{local_timestamp}:F>",
                "inline": False
            })
            
            # Environment and Version
            fields.append({
                "name": "🐳 Environment",
                "value": f"Running in Docker\nVersion: v{VERSION}",
                "inline": True
            })
            
            # Build embed
            embed = {
                "title": f"🌐 {title}",
                "description": description,
                "color": color,
                "fields": fields,
                "footer": {"text": f"WANwatcher v{VERSION} on {server_name}"},
                "timestamp": datetime.now().astimezone().isoformat()
            }
            
            # Build payload
            payload = {
                "username": self.bot_name,
                "embeds": [embed]
            }
            
            # Send request
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            
            logging.info(f"Discord notification sent successfully (Status: {response.status_code})")
            return True
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to send Discord notification: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error sending Discord notification: {e}", exc_info=True)
            return False
    
    def send_error_notification(self, error_message: str, server_name: str) -> bool:
        """Send error notification to Discord"""
        
        try:
            payload = {
                "username": self.bot_name,
                "embeds": [{
                    "title": "⚠️ WANwatcher Error",
                    "description": f"An error occurred on {server_name}",
                    "color": 15158332,  # Red
                    "fields": [
                        {
                            "name": "Error Details",
                            "value": f"```{error_message[:1000]}```",
                            "inline": False
                        },
                        {
                            "name": "🐳 Environment",
                            "value": f"Running in Docker\nVersion: v{VERSION}",
                            "inline": True
                        }
                    ],
                    "footer": {"text": f"WANwatcher v{VERSION} on {server_name}"},
                    "timestamp": datetime.now().astimezone().isoformat()
                }]
            }
            
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logging.error(f"Failed to send Discord error notification: {e}")
            return False


class TelegramNotifier(NotificationProvider):
    """Telegram bot notification provider"""
    
    def __init__(self, bot_token: str, chat_id: str, parse_mode: str = "HTML"):
        """
        Initialize Telegram notifier
        
        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Telegram chat ID to send messages to
            parse_mode: Message formatting mode (HTML or Markdown)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.parse_mode = parse_mode
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        logging.info(f"Telegram notifier initialized for chat: {chat_id}")
    
    def _format_message(self, 
                       current_ips: Dict[str, Optional[str]], 
                       previous_ips: Dict[str, Optional[str]],
                       geo_data: Optional[Dict],
                       is_first_run: bool,
                       server_name: str) -> str:
        """Format message for Telegram (HTML format)"""
        
        # Determine what changed
        ipv4_changed = current_ips.get('ipv4') != previous_ips.get('ipv4')
        ipv6_changed = current_ips.get('ipv6') != previous_ips.get('ipv6')
        
        # Determine title
        if is_first_run:
            title = "✅ Initial IP Detection"
            emoji = "🆕"
        elif ipv4_changed and ipv6_changed:
            title = "🔄 Both IP Addresses Changed"
            emoji = "⚠️"
        elif ipv4_changed:
            title = "🔄 IPv4 Address Changed"
            emoji = "⚠️"
        elif ipv6_changed:
            title = "🔄 IPv6 Address Changed"
            emoji = "⚠️"
        else:
            title = "✅ IP Status Update"
            emoji = "ℹ️"
        
        # Build message lines
        lines = [
            f"<b>{emoji} WAN IP Monitor Alert</b>",
            f"<b>{title}</b>",
            f"Monitoring for <b>{server_name}</b>\n"
        ]
        
        # IPv4 Information
        if current_ips.get('ipv4'):
            lines.append(f"📍 <b>Current IPv4:</b> <code>{current_ips['ipv4']}</code>")
            if previous_ips.get('ipv4') and ipv4_changed and not is_first_run:
                lines.append(f"📌 <b>Previous IPv4:</b> <code>{previous_ips['ipv4']}</code>")
            lines.append("")
        
        # IPv6 Information
        if current_ips.get('ipv6'):
            lines.append(f"📍 <b>Current IPv6:</b> <code>{current_ips['ipv6']}</code>")
            if previous_ips.get('ipv6') and ipv6_changed and not is_first_run:
                lines.append(f"📌 <b>Previous IPv6:</b> <code>{previous_ips['ipv6']}</code>")
            lines.append("")
        elif current_ips.get('ipv4'):
            lines.append("ℹ️ <b>IPv6 Status:</b> Not available or not configured\n")
        
        # Geographic Information
        if geo_data:
            lines.append("<b>📍 Location Information</b>")
            lines.append(f"🌍 {geo_data.get('city', 'Unknown')}, "
                        f"{geo_data.get('region', '')}, "
                        f"{geo_data.get('country', 'Unknown')}")
            lines.append(f"🏢 {geo_data.get('org', 'Unknown ISP')}")
            lines.append(f"🕐 {geo_data.get('timezone', 'Unknown')}")
            lines.append("")
        
        # Timestamp and Environment
        timestamp = datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
        lines.append(f"⏰ <b>Detected At:</b> {timestamp}")
        lines.append(f"🐳 <b>Environment:</b> Running in Docker")
        lines.append(f"📦 <b>Version:</b> v{VERSION}")
        
        return "\n".join(lines)
    
    def send_notification(self, 
                         current_ips: Dict[str, Optional[str]], 
                         previous_ips: Dict[str, Optional[str]],
                         geo_data: Optional[Dict],
                         is_first_run: bool,
                         server_name: str) -> bool:
        """Send notification via Telegram"""
        
        try:
            message = self._format_message(
                current_ips, previous_ips, geo_data, is_first_run, server_name
            )
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': self.parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            logging.info(f"Telegram notification sent successfully (Status: {response.status_code})")
            return True
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to send Telegram notification: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error sending Telegram notification: {e}", exc_info=True)
            return False
    
    def send_error_notification(self, error_message: str, server_name: str) -> bool:
        """Send error notification to Telegram"""
        
        try:
            message = (
                f"<b>⚠️ WANwatcher Error</b>\n"
                f"An error occurred on <b>{server_name}</b>\n\n"
                f"<b>Error Details:</b>\n"
                f"<code>{error_message[:500]}</code>\n\n"
                f"🐳 <b>Environment:</b> Running in Docker\n"
                f"📦 <b>Version:</b> v{VERSION}"
            )
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': self.parse_mode
            }
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logging.error(f"Failed to send Telegram error notification: {e}")
            return False
    
    def send_test_message(self) -> bool:
        """Send a test message to verify configuration"""
        
        try:
            message = (
                "<b>✅ WANwatcher Test</b>\n"
                f"Telegram notification configuration is working correctly!\n\n"
                f"📦 <b>Version:</b> v{VERSION}"
            )
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': self.parse_mode
            }
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            logging.info("Telegram test message sent successfully")
            return True
            
        except Exception as e:
            logging.error(f"Telegram test message failed: {e}")
            return False


class NotificationManager:
    """Manages multiple notification providers"""
    
    def __init__(self):
        """Initialize notification manager"""
        self.providers = []
        logging.info("Notification manager initialized")
    
    def add_provider(self, provider: NotificationProvider) -> None:
        """
        Add a notification provider
        
        Args:
            provider: NotificationProvider instance
        """
        self.providers.append(provider)
        logging.info(f"Added notification provider: {provider.__class__.__name__}")
    
    def notify_all(self, 
                   current_ips: Dict[str, Optional[str]], 
                   previous_ips: Dict[str, Optional[str]],
                   geo_data: Optional[Dict],
                   is_first_run: bool,
                   server_name: str) -> bool:
        """
        Send notification to all configured providers
        
        Returns:
            bool: True if at least one provider succeeded
        """
        if not self.providers:
            logging.warning("No notification providers configured")
            return False
        
        results = []
        for provider in self.providers:
            try:
                result = provider.send_notification(
                    current_ips, previous_ips, geo_data, is_first_run, server_name
                )
                results.append(result)
            except Exception as e:
                logging.error(
                    f"Provider {provider.__class__.__name__} failed with exception: {e}",
                    exc_info=True
                )
                results.append(False)
        
        success_count = sum(results)
        total_count = len(results)
        logging.info(f"Notification results: {success_count}/{total_count} providers succeeded")
        
        return any(results)  # Return True if at least one succeeded
    
    def notify_error(self, error_message: str, server_name: str) -> None:
        """Send error notification to all providers"""
        
        for provider in self.providers:
            try:
                provider.send_error_notification(error_message, server_name)
            except Exception as e:
                logging.error(
                    f"Error notification failed for {provider.__class__.__name__}: {e}"
                )
