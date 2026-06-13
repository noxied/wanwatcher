"""Configuration loading for WANwatcher.

All configuration comes from environment variables. This module is the single
source of truth for variable names and defaults; the validator and the
application both read from the Config object instead of os.environ directly.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


def _env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() == "true"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_list(name: str, default: str = "") -> List[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class DiscordConfig:
    enabled: bool = False
    webhook_url: str = ""
    avatar_url: str = ""

    @classmethod
    def from_env(cls) -> "DiscordConfig":
        return cls(
            enabled=_env_bool("DISCORD_ENABLED"),
            webhook_url=_env_str("DISCORD_WEBHOOK_URL"),
            avatar_url=_env_str("DISCORD_AVATAR_URL"),
        )


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""
    parse_mode: str = "HTML"

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        return cls(
            enabled=_env_bool("TELEGRAM_ENABLED"),
            bot_token=_env_str("TELEGRAM_BOT_TOKEN"),
            chat_id=_env_str("TELEGRAM_CHAT_ID"),
            parse_mode=_env_str("TELEGRAM_PARSE_MODE", "HTML") or "HTML",
        )


@dataclass
class EmailConfig:
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_addr: str = ""
    to_addrs: List[str] = field(default_factory=list)
    use_tls: bool = True
    use_ssl: bool = False
    subject_prefix: str = "[WANwatcher]"

    @classmethod
    def from_env(cls) -> "EmailConfig":
        return cls(
            enabled=_env_bool("EMAIL_ENABLED"),
            smtp_host=_env_str("EMAIL_SMTP_HOST"),
            smtp_port=_env_int("EMAIL_SMTP_PORT", 587),
            smtp_user=_env_str("EMAIL_SMTP_USER"),
            smtp_password=os.environ.get("EMAIL_SMTP_PASSWORD", ""),
            from_addr=_env_str("EMAIL_FROM"),
            to_addrs=_env_list("EMAIL_TO"),
            use_tls=_env_bool("EMAIL_USE_TLS", True),
            use_ssl=_env_bool("EMAIL_USE_SSL", False),
            subject_prefix=_env_str("EMAIL_SUBJECT_PREFIX", "[WANwatcher]")
            or "[WANwatcher]",
        )


@dataclass
class AppriseConfig:
    """Apprise opens 100+ notification services through URL strings.

    APPRISE_URLS accepts a comma-separated list, for example:
    "ntfy://host/topic,pover://user@token"
    """

    enabled: bool = False
    urls: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "AppriseConfig":
        return cls(
            enabled=_env_bool("APPRISE_ENABLED"),
            urls=_env_list("APPRISE_URLS"),
        )


@dataclass
class CloudflareConfig:
    api_token: str = ""
    zone: str = ""
    records: List[str] = field(default_factory=list)
    proxied: bool = False
    ttl: int = 1  # 1 means "automatic" in the Cloudflare API

    @classmethod
    def from_env(cls) -> "CloudflareConfig":
        return cls(
            api_token=os.environ.get("CLOUDFLARE_API_TOKEN", "").strip(),
            zone=_env_str("CLOUDFLARE_ZONE"),
            records=_env_list("CLOUDFLARE_RECORDS"),
            proxied=_env_bool("CLOUDFLARE_PROXIED", False),
            ttl=_env_int("CLOUDFLARE_TTL", 1),
        )


@dataclass
class DuckDNSConfig:
    token: str = ""
    domains: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "DuckDNSConfig":
        return cls(
            token=os.environ.get("DUCKDNS_TOKEN", "").strip(),
            domains=_env_list("DUCKDNS_DOMAINS"),
        )


@dataclass
class DynDNS2Config:
    """Generic dyndns2 protocol client (No-IP, Dynu, many routers' providers)."""

    server: str = ""
    username: str = ""
    password: str = ""
    hostnames: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "DynDNS2Config":
        return cls(
            server=_env_str("DYNDNS2_SERVER"),
            username=_env_str("DYNDNS2_USERNAME"),
            password=os.environ.get("DYNDNS2_PASSWORD", ""),
            hostnames=_env_list("DYNDNS2_HOSTNAMES"),
        )


@dataclass
class DDNSConfig:
    enabled: bool = False
    provider: str = ""  # cloudflare | duckdns | dyndns2
    cloudflare: CloudflareConfig = field(default_factory=CloudflareConfig)
    duckdns: DuckDNSConfig = field(default_factory=DuckDNSConfig)
    dyndns2: DynDNS2Config = field(default_factory=DynDNS2Config)

    @classmethod
    def from_env(cls) -> "DDNSConfig":
        return cls(
            enabled=_env_bool("DDNS_ENABLED"),
            provider=_env_str("DDNS_PROVIDER").lower(),
            cloudflare=CloudflareConfig.from_env(),
            duckdns=DuckDNSConfig.from_env(),
            dyndns2=DynDNS2Config.from_env(),
        )


@dataclass
class APIConfig:
    enabled: bool = False
    bind: str = "0.0.0.0"
    port: int = 8080

    @classmethod
    def from_env(cls) -> "APIConfig":
        return cls(
            enabled=_env_bool("API_ENABLED"),
            bind=_env_str("API_BIND", "0.0.0.0") or "0.0.0.0",
            port=_env_int("API_PORT", 8080),
        )


@dataclass
class MQTTConfig:
    enabled: bool = False
    host: str = ""
    port: int = 1883
    username: str = ""
    password: str = ""
    client_id: str = "wanwatcher"
    topic_prefix: str = "wanwatcher"
    tls: bool = False
    ha_discovery: bool = True
    ha_discovery_prefix: str = "homeassistant"

    @classmethod
    def from_env(cls) -> "MQTTConfig":
        return cls(
            enabled=_env_bool("MQTT_ENABLED"),
            host=_env_str("MQTT_HOST"),
            port=_env_int("MQTT_PORT", 1883),
            username=_env_str("MQTT_USERNAME"),
            password=os.environ.get("MQTT_PASSWORD", ""),
            client_id=_env_str("MQTT_CLIENT_ID", "wanwatcher") or "wanwatcher",
            topic_prefix=_env_str("MQTT_TOPIC_PREFIX", "wanwatcher") or "wanwatcher",
            tls=_env_bool("MQTT_TLS", False),
            ha_discovery=_env_bool("MQTT_HA_DISCOVERY", True),
            ha_discovery_prefix=_env_str("MQTT_HA_DISCOVERY_PREFIX", "homeassistant")
            or "homeassistant",
        )


@dataclass
class EventsConfig:
    notify_on_startup: bool = True
    heartbeat_enabled: bool = False
    heartbeat_interval: int = 86400
    outage_detection_enabled: bool = True
    outage_threshold: int = 3  # consecutive failed checks before declaring an outage

    @classmethod
    def from_env(cls) -> "EventsConfig":
        return cls(
            notify_on_startup=_env_bool("NOTIFY_ON_STARTUP", True),
            heartbeat_enabled=_env_bool("HEARTBEAT_ENABLED", False),
            heartbeat_interval=_env_int("HEARTBEAT_INTERVAL", 86400),
            outage_detection_enabled=_env_bool("OUTAGE_DETECTION_ENABLED", True),
            outage_threshold=_env_int("OUTAGE_THRESHOLD", 3),
        )


@dataclass
class UpdateConfig:
    enabled: bool = True
    interval: int = 86400
    on_startup: bool = True

    @classmethod
    def from_env(cls) -> "UpdateConfig":
        return cls(
            enabled=_env_bool("UPDATE_CHECK_ENABLED", True),
            interval=_env_int("UPDATE_CHECK_INTERVAL", 86400),
            on_startup=_env_bool("UPDATE_CHECK_ON_STARTUP", True),
        )


@dataclass
class Config:
    # General
    server_name: str = "WANwatcher Docker"
    bot_name: str = "WANwatcher"
    check_interval: int = 900
    monitor_ipv4: bool = True
    monitor_ipv6: bool = True
    ip_db_file: str = "/data/ipinfo.db"
    log_file: str = "/logs/wanwatcher.log"
    log_format: str = "text"  # "text" or "json"
    ipinfo_token: str = ""
    http_timeout: int = 10
    # When the detected IP differs from the stored one, confirm the change
    # with a second independent source before notifying.
    change_confirmation: bool = True

    discord: DiscordConfig = field(default_factory=DiscordConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    apprise: AppriseConfig = field(default_factory=AppriseConfig)
    ddns: DDNSConfig = field(default_factory=DDNSConfig)
    api: APIConfig = field(default_factory=APIConfig)
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    events: EventsConfig = field(default_factory=EventsConfig)
    updates: UpdateConfig = field(default_factory=UpdateConfig)

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            server_name=_env_str("SERVER_NAME", "WANwatcher Docker")
            or "WANwatcher Docker",
            bot_name=_env_str("BOT_NAME", "WANwatcher") or "WANwatcher",
            check_interval=_env_int("CHECK_INTERVAL", 900),
            monitor_ipv4=_env_bool("MONITOR_IPV4", True),
            monitor_ipv6=_env_bool("MONITOR_IPV6", True),
            ip_db_file=_env_str("IP_DB_FILE", "/data/ipinfo.db") or "/data/ipinfo.db",
            log_file=_env_str("LOG_FILE", "/logs/wanwatcher.log")
            or "/logs/wanwatcher.log",
            log_format=_env_str("LOG_FORMAT", "text").lower() or "text",
            ipinfo_token=os.environ.get("IPINFO_TOKEN", "").strip(),
            http_timeout=_env_int("HTTP_TIMEOUT", 10),
            change_confirmation=_env_bool("IP_CHANGE_CONFIRMATION", True),
            discord=DiscordConfig.from_env(),
            telegram=TelegramConfig.from_env(),
            email=EmailConfig.from_env(),
            apprise=AppriseConfig.from_env(),
            ddns=DDNSConfig.from_env(),
            api=APIConfig.from_env(),
            mqtt=MQTTConfig.from_env(),
            events=EventsConfig.from_env(),
            updates=UpdateConfig.from_env(),
        )

    def any_notifier_enabled(self) -> bool:
        return any(
            [
                self.discord.enabled,
                self.telegram.enabled,
                self.email.enabled,
                self.apprise.enabled,
            ]
        )


def redact(value: Optional[str], show_chars: int = 4) -> str:
    """Return a safe representation of a secret for logs."""
    if not value:
        return "(not set)"
    if len(value) <= show_chars:
        return "****"
    return f"{value[:show_chars]}{'*' * 8}"
