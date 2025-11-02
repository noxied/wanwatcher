#!/usr/bin/env python3
"""
WANwatcher Configuration Validator
Validates all configuration settings before startup
"""

import re
import os
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse


class ValidationError(Exception):
    """Custom exception for configuration validation errors"""
    pass


class ConfigValidator:
    """Validates WANwatcher configuration"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_url(self, url: str, name: str, require_https: bool = True) -> bool:
        """Validate URL format"""
        if not url:
            return False

        try:
            parsed = urlparse(url)

            # Check scheme
            if not parsed.scheme:
                self.errors.append(f"{name}: Missing URL scheme (http:// or https://)")
                return False

            if require_https and parsed.scheme != 'https':
                self.warnings.append(f"{name}: Using non-HTTPS URL is not recommended for security")

            # Check netloc (domain)
            if not parsed.netloc:
                self.errors.append(f"{name}: Invalid URL format (missing domain)")
                return False

            # URL length check (Discord has limits)
            if len(url) > 2048:
                self.errors.append(f"{name}: URL exceeds maximum length of 2048 characters")
                return False

            return True

        except Exception as e:
            self.errors.append(f"{name}: Invalid URL format - {str(e)}")
            return False

    def validate_email(self, email: str, name: str) -> bool:
        """Validate email address format"""
        if not email:
            return False

        # Simple but effective email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(email_pattern, email):
            self.errors.append(f"{name}: Invalid email format '{email}'")
            return False

        return True

    def validate_port(self, port: str, name: str) -> bool:
        """Validate port number"""
        try:
            port_num = int(port)
            if port_num < 1 or port_num > 65535:
                self.errors.append(f"{name}: Port must be between 1 and 65535, got {port_num}")
                return False
            return True
        except ValueError:
            self.errors.append(f"{name}: Invalid port number '{port}'")
            return False

    def validate_interval(self, interval: str, name: str, min_val: int = 60) -> bool:
        """Validate time interval in seconds"""
        try:
            interval_num = int(interval)
            if interval_num < min_val:
                self.errors.append(f"{name}: Interval must be at least {min_val} seconds, got {interval_num}")
                return False
            return True
        except ValueError:
            self.errors.append(f"{name}: Invalid interval '{interval}'")
            return False

    def validate_boolean(self, value: str, name: str) -> bool:
        """Validate boolean string"""
        if value.lower() not in ['true', 'false']:
            self.errors.append(f"{name}: Must be 'true' or 'false', got '{value}'")
            return False
        return True

    def validate_telegram_token(self, token: str) -> bool:
        """Validate Telegram bot token format"""
        if not token:
            return False

        # Telegram token format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
        # Token part is typically 35 chars but can vary (allow 30-50)
        token_pattern = r'^\d{8,10}:[A-Za-z0-9_-]{30,50}$'

        if not re.match(token_pattern, token):
            self.errors.append("TELEGRAM_BOT_TOKEN: Invalid format (should be like 123456789:ABCdefGHI...)")
            return False

        return True

    def validate_telegram_chat_id(self, chat_id: str) -> bool:
        """Validate Telegram chat ID format"""
        if not chat_id:
            return False

        # Can be numeric or @username
        if chat_id.startswith('@'):
            return True

        try:
            int(chat_id)
            return True
        except ValueError:
            self.errors.append("TELEGRAM_CHAT_ID: Must be numeric or start with @ for username")
            return False

    def validate_discord_config(self, enabled: str, webhook_url: str, avatar_url: str) -> bool:
        """Validate Discord configuration"""
        if not self.validate_boolean(enabled, "DISCORD_ENABLED"):
            return False

        if enabled.lower() == 'true':
            if not webhook_url:
                self.errors.append("DISCORD_ENABLED is true but DISCORD_WEBHOOK_URL is not set")
                return False

            if not self.validate_url(webhook_url, "DISCORD_WEBHOOK_URL", require_https=True):
                return False

            # Check if it's actually a Discord webhook URL
            if 'discord.com/api/webhooks/' not in webhook_url:
                self.warnings.append("DISCORD_WEBHOOK_URL doesn't appear to be a Discord webhook URL")

            # Validate optional avatar URL
            if avatar_url and not self.validate_url(avatar_url, "DISCORD_AVATAR_URL", require_https=False):
                return False

        return True

    def validate_telegram_config(self, enabled: str, bot_token: str, chat_id: str, parse_mode: str) -> bool:
        """Validate Telegram configuration"""
        if not self.validate_boolean(enabled, "TELEGRAM_ENABLED"):
            return False

        if enabled.lower() == 'true':
            if not bot_token:
                self.errors.append("TELEGRAM_ENABLED is true but TELEGRAM_BOT_TOKEN is not set")
                return False

            if not chat_id:
                self.errors.append("TELEGRAM_ENABLED is true but TELEGRAM_CHAT_ID is not set")
                return False

            if not self.validate_telegram_token(bot_token):
                return False

            if not self.validate_telegram_chat_id(chat_id):
                return False

            if parse_mode not in ['HTML', 'Markdown', 'MarkdownV2']:
                self.warnings.append(f"TELEGRAM_PARSE_MODE: Unknown mode '{parse_mode}', use HTML or Markdown")

        return True

    def validate_email_config(self, enabled: str, smtp_host: str, smtp_port: str,
                             smtp_user: str, smtp_password: str, from_addr: str,
                             to_addrs: str, use_tls: str, use_ssl: str) -> bool:
        """Validate Email configuration"""
        if not self.validate_boolean(enabled, "EMAIL_ENABLED"):
            return False

        if enabled.lower() == 'true':
            # Check required fields
            required_fields = {
                'EMAIL_SMTP_HOST': smtp_host,
                'EMAIL_SMTP_USER': smtp_user,
                'EMAIL_SMTP_PASSWORD': smtp_password,
                'EMAIL_FROM': from_addr,
                'EMAIL_TO': to_addrs
            }

            for field_name, field_value in required_fields.items():
                if not field_value:
                    self.errors.append(f"EMAIL_ENABLED is true but {field_name} is not set")
                    return False

            # Validate port
            if not self.validate_port(smtp_port, "EMAIL_SMTP_PORT"):
                return False

            # Validate email addresses
            if not self.validate_email(from_addr, "EMAIL_FROM"):
                return False

            # Validate TO addresses (can be comma-separated)
            for to_addr in to_addrs.split(','):
                if not self.validate_email(to_addr.strip(), "EMAIL_TO"):
                    return False

            # Validate boolean flags
            if not self.validate_boolean(use_tls, "EMAIL_USE_TLS"):
                return False

            if not self.validate_boolean(use_ssl, "EMAIL_USE_SSL"):
                return False

            # Check for conflicting TLS/SSL settings
            if use_tls.lower() == 'true' and use_ssl.lower() == 'true':
                self.errors.append("EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled")
                return False

        return True

    def validate_general_config(self, check_interval: str, monitor_ipv4: str, monitor_ipv6: str) -> bool:
        """Validate general configuration"""
        # Validate check interval (minimum 60 seconds = 1 minute)
        if not self.validate_interval(check_interval, "CHECK_INTERVAL", min_val=60):
            return False

        # Check if interval is too short
        try:
            if int(check_interval) < 300:  # 5 minutes
                self.warnings.append("CHECK_INTERVAL is less than 5 minutes - may cause excessive API calls")
        except ValueError:
            pass

        # Validate boolean flags
        if not self.validate_boolean(monitor_ipv4, "MONITOR_IPV4"):
            return False

        if not self.validate_boolean(monitor_ipv6, "MONITOR_IPV6"):
            return False

        # Check that at least one protocol is enabled
        if monitor_ipv4.lower() == 'false' and monitor_ipv6.lower() == 'false':
            self.errors.append("Both MONITOR_IPV4 and MONITOR_IPV6 are disabled - at least one must be enabled")
            return False

        return True

    def validate_update_config(self, enabled: str, interval: str, on_startup: str) -> bool:
        """Validate update check configuration"""
        if not self.validate_boolean(enabled, "UPDATE_CHECK_ENABLED"):
            return False

        if enabled.lower() == 'true':
            # Validate update check interval (minimum 1 hour)
            if not self.validate_interval(interval, "UPDATE_CHECK_INTERVAL", min_val=3600):
                return False

            if not self.validate_boolean(on_startup, "UPDATE_CHECK_ON_STARTUP"):
                return False

        return True

    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate all configuration from environment variables.
        Returns (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # Discord configuration
        discord_enabled = os.environ.get('DISCORD_ENABLED', 'false')
        discord_webhook = os.environ.get('DISCORD_WEBHOOK_URL', '')
        discord_avatar = os.environ.get('DISCORD_AVATAR_URL', '')

        self.validate_discord_config(discord_enabled, discord_webhook, discord_avatar)

        # Telegram configuration
        telegram_enabled = os.environ.get('TELEGRAM_ENABLED', 'false')
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
        telegram_parse_mode = os.environ.get('TELEGRAM_PARSE_MODE', 'HTML')

        self.validate_telegram_config(telegram_enabled, telegram_token, telegram_chat_id, telegram_parse_mode)

        # Email configuration
        email_enabled = os.environ.get('EMAIL_ENABLED', 'false')
        email_host = os.environ.get('EMAIL_SMTP_HOST', '')
        email_port = os.environ.get('EMAIL_SMTP_PORT', '587')
        email_user = os.environ.get('EMAIL_SMTP_USER', '')
        email_password = os.environ.get('EMAIL_SMTP_PASSWORD', '')
        email_from = os.environ.get('EMAIL_FROM', '')
        email_to = os.environ.get('EMAIL_TO', '')
        email_tls = os.environ.get('EMAIL_USE_TLS', 'true')
        email_ssl = os.environ.get('EMAIL_USE_SSL', 'false')

        self.validate_email_config(email_enabled, email_host, email_port, email_user,
                                   email_password, email_from, email_to, email_tls, email_ssl)

        # General configuration
        check_interval = os.environ.get('CHECK_INTERVAL', '900')
        monitor_ipv4 = os.environ.get('MONITOR_IPV4', 'true')
        monitor_ipv6 = os.environ.get('MONITOR_IPV6', 'true')

        self.validate_general_config(check_interval, monitor_ipv4, monitor_ipv6)

        # Update check configuration
        update_enabled = os.environ.get('UPDATE_CHECK_ENABLED', 'true')
        update_interval = os.environ.get('UPDATE_CHECK_INTERVAL', '86400')
        update_on_startup = os.environ.get('UPDATE_CHECK_ON_STARTUP', 'true')

        self.validate_update_config(update_enabled, update_interval, update_on_startup)

        # Check that at least one notification method is enabled
        if (discord_enabled.lower() == 'false' and
            telegram_enabled.lower() == 'false' and
            email_enabled.lower() == 'false'):
            self.errors.append("No notification methods enabled - at least one must be configured")

        # Check for enabled but misconfigured platforms
        platforms_enabled = []
        if discord_enabled.lower() == 'true' and discord_webhook:
            platforms_enabled.append('Discord')
        if telegram_enabled.lower() == 'true' and telegram_token and telegram_chat_id:
            platforms_enabled.append('Telegram')
        if email_enabled.lower() == 'true' and all([email_host, email_user, email_password, email_from, email_to]):
            platforms_enabled.append('Email')

        if not platforms_enabled:
            self.errors.append("No notification platforms properly configured - check your settings")

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings


def validate_config() -> bool:
    """
    Main validation function - validates configuration and prints results.
    Returns True if valid, False otherwise.
    """
    validator = ConfigValidator()
    is_valid, errors, warnings = validator.validate_all()

    # Print warnings
    if warnings:
        print("\n⚠️  Configuration Warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    # Print errors
    if errors:
        print("\n❌ Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease fix these errors before starting WANwatcher.\n")
        return False

    if not warnings:
        print("\n✅ Configuration validation passed!")
    else:
        print("\n✅ Configuration validation passed (with warnings)")

    return True


if __name__ == "__main__":
    """Run validator as standalone script"""
    import sys

    print("=" * 60)
    print("WANwatcher Configuration Validator")
    print("=" * 60)

    if validate_config():
        sys.exit(0)
    else:
        sys.exit(1)
