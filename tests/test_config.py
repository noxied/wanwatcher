"""Tests for wanwatcher.config: env parsing helpers, Config.from_env, redact."""

import os

import pytest

from wanwatcher.config import (
    Config,
    _env_bool,
    _env_int,
    _env_list,
    _env_str,
    redact,
)

# Every environment variable prefix the config tree reads. Cleared before
# each test so ambient variables never leak into assertions.
_ENV_PREFIXES = (
    "DISCORD_",
    "TELEGRAM_",
    "EMAIL_",
    "APPRISE_",
    "CLOUDFLARE_",
    "DUCKDNS_",
    "DYNDNS2_",
    "DDNS_",
    "API_",
    "MQTT_",
    "HEARTBEAT_",
    "OUTAGE_",
    "UPDATE_",
    "NOTIFY_",
    "MONITOR_",
    "CHECK_",
    "SERVER_",
    "BOT_",
    "IP_",
    "LOG_",
    "IPINFO_",
    "HTTP_",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith(_ENV_PREFIXES):
            monkeypatch.delenv(key, raising=False)


class TestEnvStr:
    def test_returns_value_stripped(self, monkeypatch):
        monkeypatch.setenv("X_STR", "  hello  ")
        assert _env_str("X_STR") == "hello"

    def test_returns_default_when_unset(self):
        assert _env_str("X_MISSING", "fallback") == "fallback"


class TestEnvBool:
    @pytest.mark.parametrize("raw", ["true", "True", "TRUE", "  true  "])
    def test_true_values(self, monkeypatch, raw):
        monkeypatch.setenv("X_BOOL", raw)
        assert _env_bool("X_BOOL") is True

    @pytest.mark.parametrize("raw", ["false", "False", "1", "yes", "on", ""])
    def test_anything_else_is_false(self, monkeypatch, raw):
        monkeypatch.setenv("X_BOOL", raw)
        assert _env_bool("X_BOOL") is False

    def test_unset_uses_default(self):
        assert _env_bool("X_MISSING") is False
        assert _env_bool("X_MISSING", default=True) is True


class TestEnvInt:
    def test_parses_integer(self, monkeypatch):
        monkeypatch.setenv("X_INT", "42")
        assert _env_int("X_INT", 7) == 42

    def test_garbage_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("X_INT", "abc")
        assert _env_int("X_INT", 7) == 7

    def test_empty_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("X_INT", "   ")
        assert _env_int("X_INT", 7) == 7

    def test_unset_uses_default(self):
        assert _env_int("X_MISSING", 99) == 99


class TestEnvList:
    def test_splits_on_commas_and_strips(self, monkeypatch):
        monkeypatch.setenv("X_LIST", " a, b ,c,, ")
        assert _env_list("X_LIST") == ["a", "b", "c"]

    def test_empty_yields_empty_list(self, monkeypatch):
        monkeypatch.setenv("X_LIST", "")
        assert _env_list("X_LIST") == []

    def test_unset_yields_empty_list(self):
        assert _env_list("X_MISSING") == []


class TestConfigFromEnv:
    def test_defaults(self):
        config = Config.from_env()
        assert config.server_name == "WANwatcher Docker"
        assert config.bot_name == "WANwatcher"
        assert config.check_interval == 900
        assert config.monitor_ipv4 is True
        assert config.monitor_ipv6 is True
        assert config.ip_db_file == "/data/ipinfo.db"
        assert config.http_timeout == 10
        assert config.change_confirmation is True
        assert config.discord.enabled is False
        assert config.telegram.parse_mode == "HTML"
        assert config.email.smtp_port == 587
        assert config.email.use_tls is True
        assert config.email.use_ssl is False
        assert config.apprise.urls == []
        assert config.ddns.enabled is False
        assert config.api.port == 8080
        assert config.mqtt.port == 1883
        assert config.mqtt.ha_discovery is True
        assert config.events.outage_threshold == 3
        assert config.updates.enabled is True
        assert config.updates.interval == 86400

    def test_full_tree_from_env(self, monkeypatch):
        monkeypatch.setenv("SERVER_NAME", "Casa")
        monkeypatch.setenv("CHECK_INTERVAL", "300")
        monkeypatch.setenv("MONITOR_IPV6", "false")
        monkeypatch.setenv("DISCORD_ENABLED", "true")
        monkeypatch.setenv(
            "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/a"
        )
        monkeypatch.setenv("TELEGRAM_ENABLED", "true")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100200")
        monkeypatch.setenv("EMAIL_ENABLED", "true")
        monkeypatch.setenv("EMAIL_TO", "a@example.com, b@example.com")
        monkeypatch.setenv("EMAIL_USE_TLS", "false")
        monkeypatch.setenv("APPRISE_ENABLED", "true")
        monkeypatch.setenv("APPRISE_URLS", "ntfy://host/topic,pover://u@t")
        monkeypatch.setenv("DDNS_ENABLED", "true")
        monkeypatch.setenv("DDNS_PROVIDER", "DuckDNS")
        monkeypatch.setenv("DUCKDNS_TOKEN", "tok")
        monkeypatch.setenv("DUCKDNS_DOMAINS", "myhost")
        monkeypatch.setenv("API_ENABLED", "true")
        monkeypatch.setenv("API_PORT", "9999")
        monkeypatch.setenv("MQTT_ENABLED", "true")
        monkeypatch.setenv("MQTT_HOST", "broker.local")
        monkeypatch.setenv("HEARTBEAT_ENABLED", "true")
        monkeypatch.setenv("HEARTBEAT_INTERVAL", "7200")
        monkeypatch.setenv("OUTAGE_THRESHOLD", "5")
        monkeypatch.setenv("UPDATE_CHECK_ENABLED", "false")

        config = Config.from_env()
        assert config.server_name == "Casa"
        assert config.check_interval == 300
        assert config.monitor_ipv6 is False
        assert config.discord.enabled is True
        assert config.discord.webhook_url == "https://discord.com/api/webhooks/1/a"
        assert config.telegram.chat_id == "-100200"
        assert config.email.to_addrs == ["a@example.com", "b@example.com"]
        assert config.email.use_tls is False
        assert config.apprise.urls == ["ntfy://host/topic", "pover://u@t"]
        assert config.ddns.provider == "duckdns"  # lowercased
        assert config.ddns.duckdns.token == "tok"
        assert config.ddns.duckdns.domains == ["myhost"]
        assert config.api.enabled is True
        assert config.api.port == 9999
        assert config.mqtt.host == "broker.local"
        assert config.events.heartbeat_enabled is True
        assert config.events.heartbeat_interval == 7200
        assert config.events.outage_threshold == 5
        assert config.updates.enabled is False

    def test_blank_string_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("SERVER_NAME", "   ")
        monkeypatch.setenv("BOT_NAME", "")
        config = Config.from_env()
        assert config.server_name == "WANwatcher Docker"
        assert config.bot_name == "WANwatcher"

    def test_any_notifier_enabled(self):
        config = Config.from_env()
        assert config.any_notifier_enabled() is False
        config.apprise.enabled = True
        assert config.any_notifier_enabled() is True


class TestRedact:
    def test_none_and_empty(self):
        assert redact(None) == "(not set)"
        assert redact("") == "(not set)"

    def test_short_values_are_fully_masked(self):
        assert redact("abc") == "****"
        assert redact("abcd") == "****"

    def test_long_values_show_prefix_only(self):
        result = redact("supersecrettoken")
        assert result == "supe********"
        assert "secrettoken" not in result

    def test_custom_show_chars(self):
        assert redact("supersecrettoken", show_chars=6) == "supers********"
