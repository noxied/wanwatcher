"""Notification providers for WANwatcher.

Exposes the provider classes, the manager, and build_manager(), which wires
providers from a Config object. Secrets (webhook URLs, tokens, passwords,
Apprise URLs) are never logged in full.
"""

import logging

from wanwatcher.config import Config

from .apprise import AppriseNotifier
from .base import NotificationProvider, retry_with_backoff
from .discord import DiscordNotifier
from .email import EmailNotifier
from .manager import NotificationManager
from .telegram import TelegramNotifier

__all__ = [
    "AppriseNotifier",
    "DiscordNotifier",
    "EmailNotifier",
    "NotificationManager",
    "NotificationProvider",
    "TelegramNotifier",
    "build_manager",
    "retry_with_backoff",
]

logger = logging.getLogger(__name__)


def _redact_url(url: str, show_chars: int = 8) -> str:
    """Return a loggable form of a URL: only its last few characters."""
    if not url:
        return "(not set)"
    return f"...{url[-show_chars:]}"


def build_manager(config: Config) -> NotificationManager:
    """Create a NotificationManager with providers enabled in config."""
    manager = NotificationManager()

    if config.discord.enabled:
        if config.discord.webhook_url:
            manager.add_provider(
                DiscordNotifier(
                    config.discord.webhook_url,
                    config.bot_name,
                    config.discord.avatar_url,
                )
            )
            logger.info(
                "Discord notifier enabled (webhook %s)",
                _redact_url(config.discord.webhook_url),
            )
        else:
            logger.warning(
                "Discord is enabled but DISCORD_WEBHOOK_URL is not set; skipping"
            )

    if config.telegram.enabled:
        if config.telegram.bot_token and config.telegram.chat_id:
            manager.add_provider(
                TelegramNotifier(
                    config.telegram.bot_token,
                    config.telegram.chat_id,
                    config.telegram.parse_mode,
                )
            )
            logger.info("Telegram notifier enabled")
        else:
            logger.warning(
                "Telegram is enabled but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID "
                "is not set; skipping"
            )

    if config.email.enabled:
        email = config.email
        if (
            email.smtp_host
            and email.smtp_user
            and email.smtp_password
            and email.from_addr
            and email.to_addrs
        ):
            manager.add_provider(
                EmailNotifier(
                    email.smtp_host,
                    email.smtp_port,
                    email.smtp_user,
                    email.smtp_password,
                    email.from_addr,
                    email.to_addrs,
                    email.use_tls,
                    email.use_ssl,
                    email.subject_prefix,
                )
            )
            logger.info(
                "Email notifier enabled (%d recipient(s) via %s)",
                len(email.to_addrs),
                email.smtp_host,
            )
        else:
            logger.warning(
                "Email is enabled but SMTP settings are incomplete; skipping"
            )

    if config.apprise.enabled:
        if config.apprise.urls:
            try:
                manager.add_provider(
                    AppriseNotifier(config.apprise.urls, config.bot_name)
                )
                logger.info(
                    "Apprise notifier enabled (%d URL(s))", len(config.apprise.urls)
                )
            except ImportError:
                logger.error(
                    "Apprise is enabled but the apprise package is not installed; "
                    "skipping (pip install apprise)"
                )
        else:
            logger.warning("Apprise is enabled but APPRISE_URLS is not set; skipping")

    return manager
