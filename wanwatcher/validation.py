"""Configuration validation for WANwatcher.

Validates a fully constructed :class:`wanwatcher.config.Config` object (not
``os.environ``) before the application starts. Ports the rules of the v1
``config_validator.py`` and adds checks for the v2 subsystems (Apprise, DDNS,
status API, MQTT and event settings).

Secrets (tokens, passwords, webhook URLs, Apprise URLs) are never logged in
full; only redacted fragments or scheme names appear in messages.
"""

import logging
import re
from typing import List, Tuple
from urllib.parse import urlparse

from wanwatcher.config import Config, redact

logger = logging.getLogger(__name__)

_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Telegram token format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
# Token part is typically 35 chars but can vary (allow 30-50)
_TELEGRAM_TOKEN_PATTERN = re.compile(r"^\d{8,10}:[A-Za-z0-9_-]{30,50}$")

_DDNS_PROVIDERS = ("cloudflare", "duckdns", "dyndns2")
_TELEGRAM_PARSE_MODES = ("HTML", "Markdown", "MarkdownV2")


class ValidationError(Exception):
    """Custom exception for configuration validation errors."""


class ConfigValidator:
    """Validates a WANwatcher :class:`Config` object."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []

    # -- generic helpers ----------------------------------------------------

    @staticmethod
    def redact_sensitive(value: str, show_chars: int = 4) -> str:
        """Redact sensitive information, showing only the first characters."""
        return redact(value, show_chars=show_chars)

    def validate_url(self, url: str, name: str, require_https: bool = True) -> bool:
        """Validate URL format. Adds errors/warnings under ``name``."""
        if not url:
            return False

        try:
            parsed = urlparse(url)
        except ValueError as exc:
            self.errors.append(f"{name}: Invalid URL format - {exc}")
            return False

        if not parsed.scheme:
            self.errors.append(f"{name}: Missing URL scheme (http:// or https://)")
            return False

        if require_https and parsed.scheme != "https":
            self.warnings.append(
                f"{name}: Using non-HTTPS URL is not recommended for security"
            )

        if not parsed.netloc:
            self.errors.append(f"{name}: Invalid URL format (missing domain)")
            return False

        if len(url) > 2048:
            self.errors.append(f"{name}: URL exceeds maximum length of 2048 characters")
            return False

        return True

    def validate_email(self, email: str, name: str) -> bool:
        """Validate email address format."""
        if not email or not _EMAIL_PATTERN.match(email):
            self.errors.append(f"{name}: Invalid email format")
            return False
        return True

    def validate_port(self, port: int, name: str) -> bool:
        """Validate a TCP port number."""
        if port < 1 or port > 65535:
            self.errors.append(f"{name}: Port must be between 1 and 65535, got {port}")
            return False
        return True

    # -- notification platforms ---------------------------------------------

    def validate_discord(self) -> bool:
        """Validate Discord configuration."""
        discord = self.config.discord
        if not discord.enabled:
            return True

        if not discord.webhook_url:
            self.errors.append(
                "DISCORD_ENABLED is true but DISCORD_WEBHOOK_URL is not set"
            )
            return False

        if not self.validate_url(
            discord.webhook_url, "DISCORD_WEBHOOK_URL", require_https=True
        ):
            return False

        # Check if it's actually a Discord webhook URL
        if (
            "discord.com/api/webhooks/" not in discord.webhook_url
            and "discordapp.com/api/webhooks/" not in discord.webhook_url
        ):
            self.warnings.append(
                "DISCORD_WEBHOOK_URL doesn't appear to be a Discord webhook URL"
            )

        if discord.avatar_url and not self.validate_url(
            discord.avatar_url, "DISCORD_AVATAR_URL", require_https=True
        ):
            return False

        return True

    def validate_telegram(self) -> bool:
        """Validate Telegram configuration."""
        telegram = self.config.telegram
        if not telegram.enabled:
            return True

        ok = True

        if not telegram.bot_token:
            self.errors.append(
                "TELEGRAM_ENABLED is true but TELEGRAM_BOT_TOKEN is not set"
            )
            ok = False
        elif not _TELEGRAM_TOKEN_PATTERN.match(telegram.bot_token):
            self.errors.append(
                "TELEGRAM_BOT_TOKEN: Invalid format "
                f"(got '{self.redact_sensitive(telegram.bot_token)}', "
                "should be like 123456789:ABCdefGHI...)"
            )
            ok = False

        if not telegram.chat_id:
            self.errors.append(
                "TELEGRAM_ENABLED is true but TELEGRAM_CHAT_ID is not set"
            )
            ok = False
        elif not telegram.chat_id.startswith("@"):
            try:
                int(telegram.chat_id)
            except ValueError:
                self.errors.append(
                    "TELEGRAM_CHAT_ID: Must be numeric or start with @ for username"
                )
                ok = False

        if telegram.parse_mode not in _TELEGRAM_PARSE_MODES:
            self.warnings.append(
                f"TELEGRAM_PARSE_MODE: Unknown mode '{telegram.parse_mode}', "
                "use HTML or Markdown"
            )

        return ok

    def validate_email_config(self) -> bool:
        """Validate Email/SMTP configuration."""
        email = self.config.email
        if not email.enabled:
            return True

        ok = True

        required_fields = {
            "EMAIL_SMTP_HOST": email.smtp_host,
            "EMAIL_SMTP_USER": email.smtp_user,
            "EMAIL_SMTP_PASSWORD": email.smtp_password,
            "EMAIL_FROM": email.from_addr,
        }
        for field_name, field_value in required_fields.items():
            if not field_value:
                self.errors.append(f"EMAIL_ENABLED is true but {field_name} is not set")
                ok = False

        if not email.to_addrs:
            self.errors.append("EMAIL_ENABLED is true but EMAIL_TO is not set")
            ok = False

        if not self.validate_port(email.smtp_port, "EMAIL_SMTP_PORT"):
            ok = False

        if email.from_addr and not self.validate_email(email.from_addr, "EMAIL_FROM"):
            ok = False

        for to_addr in email.to_addrs:
            if not self.validate_email(to_addr, "EMAIL_TO"):
                ok = False

        # Check for conflicting TLS/SSL settings
        if email.use_tls and email.use_ssl:
            self.errors.append("EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled")
            ok = False

        # Common port/encryption mismatches
        if email.smtp_port == 587 and not email.use_tls and not email.use_ssl:
            self.warnings.append(
                "EMAIL_SMTP_PORT 587 usually requires EMAIL_USE_TLS=true (STARTTLS)"
            )
        if email.smtp_port == 587 and email.use_ssl:
            self.warnings.append(
                "EMAIL_SMTP_PORT 587 is typically used with TLS (STARTTLS), "
                "not SSL - consider port 465 for SSL"
            )
        if email.smtp_port == 465 and not email.use_ssl:
            self.warnings.append(
                "EMAIL_SMTP_PORT 465 is typically used with EMAIL_USE_SSL=true"
            )

        return ok

    def validate_apprise(self) -> bool:
        """Validate Apprise configuration without logging full URLs."""
        apprise = self.config.apprise
        if not apprise.enabled:
            return True

        if not apprise.urls:
            self.errors.append("APPRISE_ENABLED is true but APPRISE_URLS is not set")
            return False

        ok = True
        for index, url in enumerate(apprise.urls, start=1):
            # Apprise URLs frequently embed credentials - never log them in
            # full, only reference the entry number and its scheme.
            if "://" not in url:
                self.errors.append(
                    f"APPRISE_URLS entry #{index}: Invalid Apprise URL "
                    "(missing '://' scheme separator)"
                )
                ok = False
            else:
                scheme = url.split("://", 1)[0]
                if not scheme:
                    self.errors.append(
                        f"APPRISE_URLS entry #{index} (://...): "
                        "Invalid Apprise URL (empty scheme)"
                    )
                    ok = False
                else:
                    logger.debug(
                        "APPRISE_URLS entry #%d (%s://...) looks valid", index, scheme
                    )

        return ok

    # -- v2 subsystems --------------------------------------------------------

    def validate_ddns(self) -> bool:
        """Validate dynamic DNS configuration."""
        ddns = self.config.ddns
        if not ddns.enabled:
            return True

        if ddns.provider not in _DDNS_PROVIDERS:
            self.errors.append(
                "DDNS_PROVIDER: Must be one of "
                f"{', '.join(_DDNS_PROVIDERS)}, got '{ddns.provider}'"
            )
            return False

        if ddns.provider == "cloudflare":
            return self._validate_ddns_cloudflare()
        if ddns.provider == "duckdns":
            return self._validate_ddns_duckdns()
        return self._validate_ddns_dyndns2()

    def _validate_ddns_cloudflare(self) -> bool:
        cloudflare = self.config.ddns.cloudflare
        ok = True

        if not cloudflare.api_token:
            self.errors.append(
                "DDNS provider is cloudflare but CLOUDFLARE_API_TOKEN is not set"
            )
            ok = False

        if not cloudflare.zone:
            self.errors.append(
                "DDNS provider is cloudflare but CLOUDFLARE_ZONE is not set"
            )
            ok = False

        if not cloudflare.records:
            self.errors.append(
                "DDNS provider is cloudflare but CLOUDFLARE_RECORDS is not set"
            )
            ok = False

        for record in cloudflare.records:
            if "." not in record:
                self.warnings.append(
                    f"CLOUDFLARE_RECORDS: '{record}' does not look like an FQDN "
                    "(no dot)"
                )
            if cloudflare.zone and not record.endswith(cloudflare.zone):
                self.warnings.append(
                    f"CLOUDFLARE_RECORDS: '{record}' does not end with zone "
                    f"'{cloudflare.zone}'"
                )

        return ok

    def _validate_ddns_duckdns(self) -> bool:
        duckdns = self.config.ddns.duckdns
        ok = True

        if not duckdns.token:
            self.errors.append("DDNS provider is duckdns but DUCKDNS_TOKEN is not set")
            ok = False

        if not duckdns.domains:
            self.errors.append(
                "DDNS provider is duckdns but DUCKDNS_DOMAINS is not set"
            )
            ok = False

        return ok

    def _validate_ddns_dyndns2(self) -> bool:
        dyndns2 = self.config.ddns.dyndns2
        ok = True

        if not dyndns2.server:
            self.errors.append("DDNS provider is dyndns2 but DYNDNS2_SERVER is not set")
            ok = False
        else:
            parsed = urlparse(dyndns2.server)
            if parsed.scheme != "https" or not parsed.netloc:
                self.errors.append("DYNDNS2_SERVER: Must be a valid https:// URL")
                ok = False

        if not dyndns2.username:
            self.errors.append(
                "DDNS provider is dyndns2 but DYNDNS2_USERNAME is not set"
            )
            ok = False

        if not dyndns2.password:
            self.errors.append(
                "DDNS provider is dyndns2 but DYNDNS2_PASSWORD is not set"
            )
            ok = False

        if not dyndns2.hostnames:
            self.errors.append(
                "DDNS provider is dyndns2 but DYNDNS2_HOSTNAMES is not set"
            )
            ok = False

        return ok

    def validate_api(self) -> bool:
        """Validate status API configuration."""
        api = self.config.api
        if not api.enabled:
            return True

        if not self.validate_port(api.port, "API_PORT"):
            return False

        if api.port < 1024:
            self.warnings.append(
                f"API_PORT {api.port} is a privileged port (< 1024) - "
                "may require elevated permissions"
            )

        return True

    def validate_mqtt(self) -> bool:
        """Validate MQTT configuration."""
        mqtt = self.config.mqtt
        if not mqtt.enabled:
            return True

        ok = True

        if not mqtt.host:
            self.errors.append("MQTT_ENABLED is true but MQTT_HOST is not set")
            ok = False

        if not self.validate_port(mqtt.port, "MQTT_PORT"):
            ok = False

        if not mqtt.username:
            self.warnings.append(
                "MQTT_USERNAME is not set - connecting anonymously to the broker"
            )

        return ok

    def validate_events(self) -> bool:
        """Validate event (heartbeat/outage) configuration."""
        events = self.config.events
        ok = True

        if events.heartbeat_enabled:
            if events.heartbeat_interval < 60:
                self.errors.append(
                    "HEARTBEAT_INTERVAL: Interval must be at least 60 seconds, "
                    f"got {events.heartbeat_interval}"
                )
                ok = False
            elif events.heartbeat_interval < 3600:
                self.warnings.append(
                    "HEARTBEAT_INTERVAL is less than 1 hour - may cause "
                    "notification spam"
                )

        if events.outage_threshold < 1:
            self.errors.append(
                "OUTAGE_THRESHOLD: Must be at least 1, "
                f"got {events.outage_threshold}"
            )
            ok = False

        return ok

    # -- general -------------------------------------------------------------

    def validate_general(self) -> bool:
        """Validate general (interval/protocol/timeout) configuration."""
        config = self.config
        ok = True

        # Check interval (minimum 60 seconds = 1 minute)
        if config.check_interval < 60:
            self.errors.append(
                "CHECK_INTERVAL: Interval must be at least 60 seconds, "
                f"got {config.check_interval}"
            )
            ok = False
        elif config.check_interval < 300:  # 5 minutes
            self.warnings.append(
                "CHECK_INTERVAL is less than 5 minutes - may cause excessive "
                "API calls"
            )

        if config.http_timeout < 1 or config.http_timeout > 120:
            self.errors.append(
                "HTTP_TIMEOUT: Must be between 1 and 120 seconds, "
                f"got {config.http_timeout}"
            )
            ok = False

        # Check that at least one protocol is enabled
        if not config.monitor_ipv4 and not config.monitor_ipv6:
            self.errors.append(
                "Both MONITOR_IPV4 and MONITOR_IPV6 are disabled - "
                "at least one must be enabled"
            )
            ok = False

        return ok

    def validate_updates(self) -> bool:
        """Validate update check configuration."""
        updates = self.config.updates
        if not updates.enabled:
            return True

        if updates.interval < 60:
            self.errors.append(
                "UPDATE_CHECK_INTERVAL: Interval must be at least 60 seconds, "
                f"got {updates.interval}"
            )
            return False

        if updates.interval < 3600:
            self.warnings.append(
                "UPDATE_CHECK_INTERVAL is less than 1 hour - may cause "
                "excessive GitHub API calls"
            )

        return True

    # -- entry point -----------------------------------------------------------

    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Validate the whole configuration.

        Returns (is_valid, errors, warnings).
        """
        self.errors = []
        self.warnings = []

        self.validate_discord()
        self.validate_telegram()
        self.validate_email_config()
        self.validate_apprise()
        self.validate_ddns()
        self.validate_api()
        self.validate_mqtt()
        self.validate_events()
        self.validate_general()
        self.validate_updates()

        # Check that at least one notification method is enabled
        if not self.config.any_notifier_enabled():
            self.errors.append(
                "No notification methods enabled - at least one must be configured"
            )

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings


def validate_config(config: Config) -> bool:
    """Validate a Config object and log the results.

    Returns True if the configuration is valid, False otherwise.
    """
    validator = ConfigValidator(config)
    is_valid, errors, warnings = validator.validate_all()

    if warnings:
        logger.warning("Configuration validation found %d warning(s):", len(warnings))
        for warning in warnings:
            logger.warning("  - %s", warning)

    if errors:
        logger.error("Configuration validation found %d error(s):", len(errors))
        for error in errors:
            logger.error("  - %s", error)
        logger.error("Please fix these errors before starting WANwatcher.")
        return False

    if warnings:
        logger.info("Configuration validation passed (with warnings)")
    else:
        logger.info("Configuration validation passed")

    return is_valid


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    from wanwatcher.config import Config as _Config

    sys.exit(0 if validate_config(_Config.from_env()) else 1)
