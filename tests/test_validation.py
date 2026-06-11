"""Tests for wanwatcher.validation.

Ports the spirit of the v1 config_validator tests (URLs, email, ports,
intervals, per-platform rules) and adds coverage for the v2 subsystems
(Apprise, DDNS, status API, MQTT, heartbeat/outage events).
"""

import pytest

from wanwatcher.config import (
    AppriseConfig,
    CloudflareConfig,
    Config,
    DDNSConfig,
    DiscordConfig,
    DuckDNSConfig,
    DynDNS2Config,
    EmailConfig,
    TelegramConfig,
)
from wanwatcher.validation import ConfigValidator, validate_config

VALID_WEBHOOK = "https://discord.com/api/webhooks/123456/abcdef"
VALID_TELEGRAM_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz_1234567"


def make_config(**overrides) -> Config:
    """A minimal valid config: Discord enabled with a proper webhook."""
    config = Config(discord=DiscordConfig(enabled=True, webhook_url=VALID_WEBHOOK))
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def run(config: Config):
    return ConfigValidator(config).validate_all()


class TestURLValidation:
    def setup_method(self):
        self.validator = ConfigValidator(make_config())

    def test_valid_https_url(self):
        assert self.validator.validate_url(VALID_WEBHOOK, "TEST_URL")
        assert self.validator.errors == []

    def test_http_url_passes_with_warning(self):
        assert self.validator.validate_url("http://example.com/hook", "TEST_URL")
        assert any("non-HTTPS" in warning for warning in self.validator.warnings)

    def test_url_without_scheme_fails(self):
        assert not self.validator.validate_url("discord.com/webhook", "TEST_URL")
        assert self.validator.errors

    def test_url_without_domain_fails(self):
        assert not self.validator.validate_url("https://", "TEST_URL")
        assert self.validator.errors

    def test_url_too_long_fails(self):
        long_url = "https://example.com/" + "a" * 2100
        assert not self.validator.validate_url(long_url, "TEST_URL")
        assert any("maximum length" in error for error in self.validator.errors)


class TestEmailAddressValidation:
    def setup_method(self):
        self.validator = ConfigValidator(make_config())

    @pytest.mark.parametrize(
        "address", ["user@example.com", "user+tag@example.com", "a.b@sub.example.org"]
    )
    def test_valid_addresses(self, address):
        assert self.validator.validate_email(address, "TEST_EMAIL")

    @pytest.mark.parametrize(
        "address", ["userexample.com", "user@", "user@example", "", "@example.com"]
    )
    def test_invalid_addresses(self, address):
        assert not self.validator.validate_email(address, "TEST_EMAIL")
        assert self.validator.errors


class TestPortValidation:
    def setup_method(self):
        self.validator = ConfigValidator(make_config())

    @pytest.mark.parametrize("port", [1, 587, 65535])
    def test_valid_ports(self, port):
        assert self.validator.validate_port(port, "TEST_PORT")

    @pytest.mark.parametrize("port", [0, -1, 65536])
    def test_invalid_ports(self, port):
        assert not self.validator.validate_port(port, "TEST_PORT")
        assert self.validator.errors


class TestDiscordValidation:
    def test_valid_webhook_passes(self):
        is_valid, errors, _ = run(make_config())
        assert is_valid, errors

    def test_disabled_discord_is_skipped(self):
        config = make_config()
        config.discord.enabled = False
        config.telegram = TelegramConfig(
            enabled=True, bot_token=VALID_TELEGRAM_TOKEN, chat_id="12345"
        )
        is_valid, errors, _ = run(config)
        assert is_valid, errors

    def test_enabled_without_webhook_fails(self):
        config = make_config()
        config.discord.webhook_url = ""
        is_valid, errors, _ = run(config)
        assert not is_valid
        assert any("DISCORD_WEBHOOK_URL is not set" in error for error in errors)

    def test_non_discord_url_warns(self):
        config = make_config()
        config.discord.webhook_url = "https://example.com/webhook"
        is_valid, _, warnings = run(config)
        assert is_valid
        assert any("doesn't appear to be a Discord webhook" in w for w in warnings)

    def test_invalid_avatar_url_fails(self):
        config = make_config()
        config.discord.avatar_url = "not-a-url"
        is_valid, errors, _ = run(config)
        assert not is_valid
        assert any("DISCORD_AVATAR_URL" in error for error in errors)


class TestTelegramValidation:
    def make_telegram_config(self, **overrides) -> Config:
        telegram = TelegramConfig(
            enabled=True, bot_token=VALID_TELEGRAM_TOKEN, chat_id="123456789"
        )
        for key, value in overrides.items():
            setattr(telegram, key, value)
        return Config(telegram=telegram)

    def test_valid_telegram_passes(self):
        is_valid, errors, _ = run(self.make_telegram_config())
        assert is_valid, errors

    def test_invalid_token_format_fails(self):
        is_valid, errors, _ = run(self.make_telegram_config(bot_token="invalid_token"))
        assert not is_valid
        assert any("TELEGRAM_BOT_TOKEN" in error for error in errors)

    def test_token_never_logged_in_full(self):
        is_valid, errors, _ = run(
            self.make_telegram_config(bot_token="totally_invalid_secret_token_value")
        )
        assert not is_valid
        assert not any("totally_invalid_secret_token_value" in e for e in errors)

    def test_missing_token_fails(self):
        is_valid, errors, _ = run(self.make_telegram_config(bot_token=""))
        assert not is_valid
        assert any("TELEGRAM_BOT_TOKEN is not set" in error for error in errors)

    def test_username_chat_id_passes(self):
        is_valid, errors, _ = run(self.make_telegram_config(chat_id="@mychannel"))
        assert is_valid, errors

    def test_negative_numeric_chat_id_passes(self):
        is_valid, errors, _ = run(self.make_telegram_config(chat_id="-1001234567890"))
        assert is_valid, errors

    def test_non_numeric_chat_id_fails(self):
        is_valid, errors, _ = run(self.make_telegram_config(chat_id="not numeric"))
        assert not is_valid
        assert any("TELEGRAM_CHAT_ID" in error for error in errors)

    def test_unknown_parse_mode_warns(self):
        is_valid, _, warnings = run(self.make_telegram_config(parse_mode="BBCode"))
        assert is_valid
        assert any("TELEGRAM_PARSE_MODE" in warning for warning in warnings)


class TestEmailConfigValidation:
    def make_email_config(self, **overrides) -> Config:
        email = EmailConfig(
            enabled=True,
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
            use_tls=True,
            use_ssl=False,
        )
        for key, value in overrides.items():
            setattr(email, key, value)
        return Config(email=email)

    def test_valid_email_config_passes(self):
        is_valid, errors, _ = run(self.make_email_config())
        assert is_valid, errors

    @pytest.mark.parametrize(
        "field,env_name",
        [
            ("smtp_host", "EMAIL_SMTP_HOST"),
            ("smtp_user", "EMAIL_SMTP_USER"),
            ("smtp_password", "EMAIL_SMTP_PASSWORD"),
            ("from_addr", "EMAIL_FROM"),
        ],
    )
    def test_missing_required_field_fails(self, field, env_name):
        is_valid, errors, _ = run(self.make_email_config(**{field: ""}))
        assert not is_valid
        assert any(env_name in error for error in errors)

    def test_missing_recipients_fails(self):
        is_valid, errors, _ = run(self.make_email_config(to_addrs=[]))
        assert not is_valid
        assert any("EMAIL_TO is not set" in error for error in errors)

    def test_invalid_recipient_fails(self):
        is_valid, errors, _ = run(self.make_email_config(to_addrs=["bad-address"]))
        assert not is_valid
        assert any("EMAIL_TO" in error for error in errors)

    def test_tls_and_ssl_conflict_fails(self):
        is_valid, errors, _ = run(self.make_email_config(use_tls=True, use_ssl=True))
        assert not is_valid
        assert any("cannot both be enabled" in error for error in errors)

    def test_invalid_port_fails(self):
        is_valid, errors, _ = run(self.make_email_config(smtp_port=0))
        assert not is_valid
        assert any("EMAIL_SMTP_PORT" in error for error in errors)

    def test_port_465_without_ssl_warns(self):
        is_valid, errors, warnings = run(self.make_email_config(smtp_port=465))
        assert is_valid, errors
        assert any("465" in warning for warning in warnings)

    def test_port_587_without_encryption_warns(self):
        is_valid, _, warnings = run(
            self.make_email_config(use_tls=False, use_ssl=False)
        )
        assert is_valid
        assert any("587" in warning for warning in warnings)


class TestAppriseValidation:
    def make_apprise_config(self, urls) -> Config:
        return Config(apprise=AppriseConfig(enabled=True, urls=urls))

    def test_valid_urls_pass(self):
        is_valid, errors, _ = run(
            self.make_apprise_config(["ntfy://host/topic", "pover://user@token"])
        )
        assert is_valid, errors

    def test_enabled_without_urls_fails(self):
        is_valid, errors, _ = run(self.make_apprise_config([]))
        assert not is_valid
        assert any("APPRISE_URLS is not set" in error for error in errors)

    def test_url_without_scheme_separator_fails(self):
        is_valid, errors, _ = run(self.make_apprise_config(["not-an-apprise-url"]))
        assert not is_valid
        assert any("entry #1" in error for error in errors)

    def test_url_with_empty_scheme_fails(self):
        is_valid, errors, _ = run(self.make_apprise_config(["://host/topic"]))
        assert not is_valid

    def test_credentials_never_appear_in_errors(self):
        is_valid, errors, _ = run(
            self.make_apprise_config(["secret-user:secret-pass-no-scheme"])
        )
        assert not is_valid
        assert not any("secret-pass" in error for error in errors)


class TestDDNSValidation:
    def make_ddns_config(self, ddns: DDNSConfig) -> Config:
        return make_config(ddns=ddns)

    def test_disabled_ddns_is_skipped(self):
        is_valid, errors, _ = run(self.make_ddns_config(DDNSConfig(enabled=False)))
        assert is_valid, errors

    def test_unknown_provider_fails(self):
        is_valid, errors, _ = run(
            self.make_ddns_config(DDNSConfig(enabled=True, provider="route53"))
        )
        assert not is_valid
        assert any("DDNS_PROVIDER" in error for error in errors)

    def test_cloudflare_valid(self):
        ddns = DDNSConfig(
            enabled=True,
            provider="cloudflare",
            cloudflare=CloudflareConfig(
                api_token="token", zone="example.com", records=["home.example.com"]
            ),
        )
        is_valid, errors, _ = run(self.make_ddns_config(ddns))
        assert is_valid, errors

    def test_cloudflare_missing_fields_fail(self):
        ddns = DDNSConfig(enabled=True, provider="cloudflare")
        is_valid, errors, _ = run(self.make_ddns_config(ddns))
        assert not is_valid
        joined = " ".join(errors)
        assert "CLOUDFLARE_API_TOKEN" in joined
        assert "CLOUDFLARE_ZONE" in joined
        assert "CLOUDFLARE_RECORDS" in joined

    def test_cloudflare_record_outside_zone_warns(self):
        ddns = DDNSConfig(
            enabled=True,
            provider="cloudflare",
            cloudflare=CloudflareConfig(
                api_token="token", zone="example.com", records=["host.other.net"]
            ),
        )
        is_valid, errors, warnings = run(self.make_ddns_config(ddns))
        assert is_valid, errors
        assert any("does not end with zone" in warning for warning in warnings)

    def test_duckdns_valid(self):
        ddns = DDNSConfig(
            enabled=True,
            provider="duckdns",
            duckdns=DuckDNSConfig(token="tok", domains=["myhost"]),
        )
        is_valid, errors, _ = run(self.make_ddns_config(ddns))
        assert is_valid, errors

    def test_duckdns_missing_fields_fail(self):
        ddns = DDNSConfig(enabled=True, provider="duckdns")
        is_valid, errors, _ = run(self.make_ddns_config(ddns))
        assert not is_valid
        joined = " ".join(errors)
        assert "DUCKDNS_TOKEN" in joined
        assert "DUCKDNS_DOMAINS" in joined

    def test_dyndns2_valid(self):
        ddns = DDNSConfig(
            enabled=True,
            provider="dyndns2",
            dyndns2=DynDNS2Config(
                server="https://dynupdate.no-ip.com",
                username="user",
                password="pass",
                hostnames=["host.ddns.net"],
            ),
        )
        is_valid, errors, _ = run(self.make_ddns_config(ddns))
        assert is_valid, errors

    def test_dyndns2_http_server_fails(self):
        ddns = DDNSConfig(
            enabled=True,
            provider="dyndns2",
            dyndns2=DynDNS2Config(
                server="http://dynupdate.no-ip.com",
                username="user",
                password="pass",
                hostnames=["host.ddns.net"],
            ),
        )
        is_valid, errors, _ = run(self.make_ddns_config(ddns))
        assert not is_valid
        assert any("DYNDNS2_SERVER" in error for error in errors)

    def test_dyndns2_missing_fields_fail(self):
        ddns = DDNSConfig(enabled=True, provider="dyndns2")
        is_valid, errors, _ = run(self.make_ddns_config(ddns))
        assert not is_valid
        joined = " ".join(errors)
        for name in (
            "DYNDNS2_SERVER",
            "DYNDNS2_USERNAME",
            "DYNDNS2_PASSWORD",
            "DYNDNS2_HOSTNAMES",
        ):
            assert name in joined


class TestAPIValidation:
    def test_valid_api_port_passes(self):
        config = make_config()
        config.api.enabled = True
        config.api.port = 8080
        is_valid, errors, _ = run(config)
        assert is_valid, errors

    def test_out_of_range_port_fails(self):
        config = make_config()
        config.api.enabled = True
        config.api.port = 70000
        is_valid, errors, _ = run(config)
        assert not is_valid
        assert any("API_PORT" in error for error in errors)

    def test_privileged_port_warns(self):
        config = make_config()
        config.api.enabled = True
        config.api.port = 80
        is_valid, _, warnings = run(config)
        assert is_valid
        assert any("privileged port" in warning for warning in warnings)


class TestMQTTValidation:
    def test_valid_mqtt_passes(self):
        config = make_config()
        config.mqtt.enabled = True
        config.mqtt.host = "broker.local"
        config.mqtt.username = "user"
        is_valid, errors, _ = run(config)
        assert is_valid, errors

    def test_missing_host_fails(self):
        config = make_config()
        config.mqtt.enabled = True
        is_valid, errors, _ = run(config)
        assert not is_valid
        assert any("MQTT_HOST is not set" in error for error in errors)

    def test_anonymous_connection_warns(self):
        config = make_config()
        config.mqtt.enabled = True
        config.mqtt.host = "broker.local"
        is_valid, _, warnings = run(config)
        assert is_valid
        assert any("MQTT_USERNAME" in warning for warning in warnings)

    def test_bad_port_fails(self):
        config = make_config()
        config.mqtt.enabled = True
        config.mqtt.host = "broker.local"
        config.mqtt.port = 0
        is_valid, errors, _ = run(config)
        assert not is_valid
        assert any("MQTT_PORT" in error for error in errors)


class TestEventsValidation:
    def test_heartbeat_interval_too_low_fails(self):
        config = make_config()
        config.events.heartbeat_enabled = True
        config.events.heartbeat_interval = 30
        is_valid, errors, _ = run(config)
        assert not is_valid
        assert any("HEARTBEAT_INTERVAL" in error for error in errors)

    def test_short_heartbeat_interval_warns(self):
        config = make_config()
        config.events.heartbeat_enabled = True
        config.events.heartbeat_interval = 600
        is_valid, _, warnings = run(config)
        assert is_valid
        assert any("HEARTBEAT_INTERVAL" in warning for warning in warnings)

    def test_heartbeat_disabled_skips_interval_check(self):
        config = make_config()
        config.events.heartbeat_enabled = False
        config.events.heartbeat_interval = 1
        is_valid, errors, _ = run(config)
        assert is_valid, errors

    def test_outage_threshold_below_one_fails(self):
        config = make_config()
        config.events.outage_threshold = 0
        is_valid, errors, _ = run(config)
        assert not is_valid
        assert any("OUTAGE_THRESHOLD" in error for error in errors)


class TestGeneralValidation:
    def test_check_interval_below_minimum_fails(self):
        is_valid, errors, _ = run(make_config(check_interval=30))
        assert not is_valid
        assert any("CHECK_INTERVAL" in error for error in errors)

    def test_check_interval_at_minimum_passes(self):
        is_valid, errors, _ = run(make_config(check_interval=60))
        assert is_valid, errors

    def test_short_check_interval_warns(self):
        is_valid, _, warnings = run(make_config(check_interval=120))
        assert is_valid
        assert any("CHECK_INTERVAL" in warning for warning in warnings)

    @pytest.mark.parametrize("timeout", [0, 121])
    def test_http_timeout_out_of_range_fails(self, timeout):
        is_valid, errors, _ = run(make_config(http_timeout=timeout))
        assert not is_valid
        assert any("HTTP_TIMEOUT" in error for error in errors)

    def test_both_protocols_disabled_fails(self):
        is_valid, errors, _ = run(make_config(monitor_ipv4=False, monitor_ipv6=False))
        assert not is_valid
        assert any("at least one must be enabled" in error for error in errors)

    def test_no_notifier_enabled_fails(self):
        is_valid, errors, _ = run(Config())
        assert not is_valid
        assert any("No notification methods enabled" in error for error in errors)


class TestUpdatesValidation:
    def test_update_interval_too_low_fails(self):
        config = make_config()
        config.updates.interval = 30
        is_valid, errors, _ = run(config)
        assert not is_valid
        assert any("UPDATE_CHECK_INTERVAL" in error for error in errors)

    def test_short_update_interval_warns(self):
        config = make_config()
        config.updates.interval = 600
        is_valid, _, warnings = run(config)
        assert is_valid
        assert any("UPDATE_CHECK_INTERVAL" in warning for warning in warnings)

    def test_disabled_updates_skip_interval_check(self):
        config = make_config()
        config.updates.enabled = False
        config.updates.interval = 1
        is_valid, errors, _ = run(config)
        assert is_valid, errors


class TestValidateConfigFunction:
    def test_returns_true_for_valid_config(self):
        assert validate_config(make_config()) is True

    def test_returns_false_for_invalid_config(self):
        assert validate_config(Config()) is False

    def test_logs_errors_without_crashing(self, caplog):
        with caplog.at_level("ERROR", logger="wanwatcher.validation"):
            validate_config(Config())
        assert "error" in caplog.text.lower()
