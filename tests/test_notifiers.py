"""Tests for wanwatcher.notifiers: retry, manager fan-out, providers."""

import sys
import types
from unittest.mock import Mock, patch

import pytest
import requests

from wanwatcher.config import Config, DiscordConfig, EmailConfig, TelegramConfig
from wanwatcher.notifiers import (
    DiscordNotifier,
    EmailNotifier,
    NotificationManager,
    NotificationProvider,
    TelegramNotifier,
    build_manager,
    retry_with_backoff,
)

CURRENT_IPS = {"ipv4": "9.9.9.9", "ipv6": None}
PREVIOUS_IPS = {"ipv4": "8.8.8.8", "ipv6": None}
UPDATE_INFO = {
    "current_version": "2.0.0",
    "latest_version": "2.1.0",
    "release_name": "v2.1.0",
    "release_url": "https://github.com/noxied/wanwatcher/releases/tag/v2.1.0",
    "release_body": "- New feature\n- Bug fix",
    "published_at": "2026-06-01T00:00:00Z",
}


@pytest.fixture(autouse=True)
def no_sleep():
    """Keep retry backoff instantaneous in every test in this module."""
    with patch("wanwatcher.notifiers.base.time.sleep") as mock_sleep:
        yield mock_sleep


# -- retry_with_backoff -------------------------------------------------------


class TestRetryWithBackoff:
    def test_success_on_first_attempt(self, no_sleep):
        func = Mock(return_value=True)
        assert retry_with_backoff(func) is True
        assert func.call_count == 1
        no_sleep.assert_not_called()

    def test_success_after_false_then_true(self, no_sleep):
        func = Mock(side_effect=[False, True])
        assert retry_with_backoff(func) is True
        assert func.call_count == 2
        no_sleep.assert_called_once_with(1.0)

    def test_success_after_exception(self, no_sleep):
        func = Mock(side_effect=[RuntimeError("boom"), True])
        assert retry_with_backoff(func) is True
        assert func.call_count == 2

    def test_exhaustion_returns_false(self, no_sleep):
        func = Mock(return_value=False)
        assert retry_with_backoff(func, max_retries=3) is False
        assert func.call_count == 3
        # Sleeps between attempts only, with exponential delays.
        assert [call.args[0] for call in no_sleep.call_args_list] == [1.0, 2.0]

    def test_exhaustion_with_exceptions_returns_false(self, no_sleep):
        func = Mock(side_effect=RuntimeError("boom"))
        assert retry_with_backoff(func, max_retries=3) is False
        assert func.call_count == 3

    def test_custom_base_delay(self, no_sleep):
        func = Mock(side_effect=[False, False, True])
        assert retry_with_backoff(func, max_retries=3, base_delay=2.0) is True
        assert [call.args[0] for call in no_sleep.call_args_list] == [2.0, 4.0]


# -- NotificationManager -----------------------------------------------------


class RecordingProviderA(NotificationProvider):
    name = "rec_a"

    def __init__(self):
        self.notification_calls = []
        self.update_calls = []
        self.event_calls = []

    def send_notification(self, *args, **kwargs):
        self.notification_calls.append((args, kwargs))
        return True

    def send_update_notification(self, *args, **kwargs):
        self.update_calls.append((args, kwargs))
        return True

    def send_event(self, *args, **kwargs):
        self.event_calls.append((args, kwargs))
        return True


class RecordingProviderB(RecordingProviderA):
    name = "rec_b"


class AlwaysFailingProvider(NotificationProvider):
    name = "failing"

    def send_notification(self, *args, **kwargs):
        raise RuntimeError("provider exploded")

    def send_update_notification(self, *args, **kwargs):
        raise RuntimeError("provider exploded")

    def send_event(self, *args, **kwargs):
        raise RuntimeError("provider exploded")


class TestNotificationManager:
    def test_fan_out_reaches_every_provider(self):
        """Each distinct provider instance must receive its own call.

        Guards against late-binding closure bugs where every retry closure
        captures the loop variable and only the last provider gets called.
        """
        provider_a = RecordingProviderA()
        provider_b = RecordingProviderB()
        manager = NotificationManager()
        manager.add_provider(provider_a)
        manager.add_provider(provider_b)

        results = manager.send_to_all(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )

        assert results == {"RecordingProviderA": True, "RecordingProviderB": True}
        assert len(provider_a.notification_calls) == 1
        assert len(provider_b.notification_calls) == 1
        args, _ = provider_a.notification_calls[0]
        assert args == (CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0")

    def test_failing_provider_is_isolated(self):
        provider_b = RecordingProviderB()
        manager = NotificationManager()
        manager.add_provider(AlwaysFailingProvider())
        manager.add_provider(provider_b)

        results = manager.send_to_all(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )

        assert results["AlwaysFailingProvider"] is False
        assert results["RecordingProviderB"] is True
        assert len(provider_b.notification_calls) == 1

    def test_notify_update_fans_out(self):
        provider_a = RecordingProviderA()
        provider_b = RecordingProviderB()
        manager = NotificationManager()
        manager.add_provider(provider_a)
        manager.add_provider(provider_b)

        results = manager.notify_update(UPDATE_INFO, "Server", "2.0.0")

        assert all(results.values())
        assert len(provider_a.update_calls) == 1
        assert len(provider_b.update_calls) == 1

    def test_notify_event_fans_out(self):
        provider_a = RecordingProviderA()
        provider_b = RecordingProviderB()
        manager = NotificationManager()
        manager.add_provider(provider_a)
        manager.add_provider(provider_b)

        results = manager.notify_event("Title", "Body", "Server", severity="warning")

        assert all(results.values())
        assert provider_a.event_calls[0][0] == ("Title", "Body", "Server", "warning")
        assert provider_b.event_calls[0][0] == ("Title", "Body", "Server", "warning")

    def test_notify_all_alias(self):
        provider_a = RecordingProviderA()
        manager = NotificationManager()
        manager.add_provider(provider_a)
        results = manager.notify_all(
            CURRENT_IPS, PREVIOUS_IPS, None, True, "Server", "2.0.0"
        )
        assert results == {"RecordingProviderA": True}

    def test_no_providers_returns_empty_results(self):
        manager = NotificationManager()
        assert manager.send_to_all({}, {}, None, True, "Server") == {}


# -- build_manager ------------------------------------------------------------


class TestBuildManager:
    def test_empty_config_builds_no_providers(self):
        manager = build_manager(Config())
        assert manager.providers == []

    def test_discord_provider_registered(self):
        config = Config(
            discord=DiscordConfig(
                enabled=True, webhook_url="https://discord.com/api/webhooks/1/a"
            )
        )
        manager = build_manager(config)
        assert len(manager.providers) == 1
        assert isinstance(manager.providers[0], DiscordNotifier)

    def test_discord_enabled_without_webhook_is_skipped(self):
        config = Config(discord=DiscordConfig(enabled=True, webhook_url=""))
        manager = build_manager(config)
        assert manager.providers == []

    def test_telegram_provider_registered(self):
        config = Config(
            telegram=TelegramConfig(enabled=True, bot_token="123:abc", chat_id="42")
        )
        manager = build_manager(config)
        assert len(manager.providers) == 1
        assert isinstance(manager.providers[0], TelegramNotifier)

    def test_telegram_missing_chat_id_is_skipped(self):
        config = Config(
            telegram=TelegramConfig(enabled=True, bot_token="123:abc", chat_id="")
        )
        assert build_manager(config).providers == []

    def test_email_provider_registered(self):
        config = Config(
            email=EmailConfig(
                enabled=True,
                smtp_host="smtp.example.com",
                smtp_user="user",
                smtp_password="pass",
                from_addr="from@example.com",
                to_addrs=["to@example.com"],
            )
        )
        manager = build_manager(config)
        assert len(manager.providers) == 1
        assert isinstance(manager.providers[0], EmailNotifier)

    def test_email_incomplete_settings_skipped(self):
        config = Config(email=EmailConfig(enabled=True, smtp_host="smtp.example.com"))
        assert build_manager(config).providers == []

    def test_multiple_providers_registered_together(self):
        config = Config(
            discord=DiscordConfig(
                enabled=True, webhook_url="https://discord.com/api/webhooks/1/a"
            ),
            telegram=TelegramConfig(enabled=True, bot_token="123:abc", chat_id="42"),
        )
        manager = build_manager(config)
        assert {type(p) for p in manager.providers} == {
            DiscordNotifier,
            TelegramNotifier,
        }

    def test_apprise_enabled_without_package_is_skipped(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "apprise", None)  # force ImportError
        config = Config()
        config.apprise.enabled = True
        config.apprise.urls = ["ntfy://host/topic"]
        manager = build_manager(config)
        assert manager.providers == []


# -- DiscordNotifier ----------------------------------------------------------


@patch("wanwatcher.notifiers.discord.requests.post")
class TestDiscordNotifier:
    def make_notifier(self, **kwargs):
        return DiscordNotifier("https://discord.com/api/webhooks/1/a", **kwargs)

    def test_send_notification_success_on_204(self, mock_post):
        mock_post.return_value = Mock(status_code=204)
        notifier = self.make_notifier()
        assert notifier.send_notification(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )
        payload = mock_post.call_args.kwargs["json"]
        assert payload["username"] == "WANwatcher"
        assert "avatar_url" not in payload
        description = payload["embeds"][0]["description"]
        assert "8.8.8.8" in description and "9.9.9.9" in description

    def test_send_notification_first_run(self, mock_post):
        mock_post.return_value = Mock(status_code=204)
        notifier = self.make_notifier()
        assert notifier.send_notification(
            CURRENT_IPS, {}, None, True, "Server", "2.0.0"
        )
        description = mock_post.call_args.kwargs["json"]["embeds"][0]["description"]
        assert "Initial IP Detection" in description

    def test_send_notification_failure_on_error_status(self, mock_post):
        mock_post.return_value = Mock(status_code=400, text="bad request")
        notifier = self.make_notifier()
        assert not notifier.send_notification(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )

    def test_send_notification_handles_exception(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("down")
        notifier = self.make_notifier()
        assert not notifier.send_notification(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )

    def test_custom_avatar_included(self, mock_post):
        mock_post.return_value = Mock(status_code=204)
        notifier = self.make_notifier(avatar_url="https://example.com/avatar.png")
        notifier.send_notification(CURRENT_IPS, {}, None, True, "Server", "2.0.0")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["avatar_url"] == "https://example.com/avatar.png"

    def test_send_update_notification(self, mock_post):
        mock_post.return_value = Mock(status_code=204)
        notifier = self.make_notifier()
        assert notifier.send_update_notification(UPDATE_INFO, "Server", "2.0.0")
        fields = mock_post.call_args.kwargs["json"]["embeds"][0]["fields"]
        values = " ".join(str(field["value"]) for field in fields)
        assert "v2.1.0" in values

    @pytest.mark.parametrize(
        "severity,color",
        [("info", 3447003), ("warning", 15105570), ("error", 15158332)],
    )
    def test_send_event_severity_colors(self, mock_post, severity, color):
        mock_post.return_value = Mock(status_code=204)
        notifier = self.make_notifier()
        assert notifier.send_event("Title", "Message", "Server", severity=severity)
        embed = mock_post.call_args.kwargs["json"]["embeds"][0]
        assert embed["color"] == color
        assert embed["title"] == "Title"

    def test_send_event_unknown_severity_defaults_to_info(self, mock_post):
        mock_post.return_value = Mock(status_code=204)
        notifier = self.make_notifier()
        notifier.send_event("Title", "Message", "Server", severity="critical")
        assert mock_post.call_args.kwargs["json"]["embeds"][0]["color"] == 3447003


# -- TelegramNotifier ---------------------------------------------------------


BOT_TOKEN = "123456789:SECRETtokenSECRETtokenSECRETtoken"


@patch("wanwatcher.notifiers.telegram.requests.post")
class TestTelegramNotifier:
    def make_notifier(self):
        return TelegramNotifier(BOT_TOKEN, "424242", parse_mode="HTML")

    def test_send_notification_success_on_200(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        notifier = self.make_notifier()
        assert notifier.send_notification(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )
        url = mock_post.call_args.args[0]
        assert url == f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = mock_post.call_args.kwargs["json"]
        assert payload["chat_id"] == "424242"
        assert payload["parse_mode"] == "HTML"
        assert "9.9.9.9" in payload["text"]

    def test_send_notification_failure_on_error_status(self, mock_post):
        mock_post.return_value = Mock(status_code=403, text="forbidden")
        notifier = self.make_notifier()
        assert not notifier.send_notification(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )

    def test_send_update_notification_success(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        notifier = self.make_notifier()
        assert notifier.send_update_notification(UPDATE_INFO, "Server", "2.0.0")
        assert "v2.1.0" in mock_post.call_args.kwargs["json"]["text"]

    def test_send_event_success(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        notifier = self.make_notifier()
        assert notifier.send_event("Heartbeat", "Still alive", "Server")
        text = mock_post.call_args.kwargs["json"]["text"]
        assert "Heartbeat" in text and "Still alive" in text

    def test_token_never_leaks_into_logs_on_connection_error(self, mock_post, caplog):
        # requests exceptions embed the full request URL (which contains the
        # bot token), so the provider must only log the exception type.
        mock_post.side_effect = requests.exceptions.ConnectionError(
            f"HTTPSConnectionPool: https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        )
        notifier = self.make_notifier()
        with caplog.at_level("DEBUG"):
            result = notifier.send_notification(
                CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
            )
        assert result is False
        assert BOT_TOKEN not in caplog.text
        assert "SECRETtoken" not in caplog.text

    def test_token_never_leaks_from_send_event(self, mock_post, caplog):
        mock_post.side_effect = requests.exceptions.Timeout(
            f"url: https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        )
        notifier = self.make_notifier()
        with caplog.at_level("DEBUG"):
            assert not notifier.send_event("Title", "Message", "Server")
        assert BOT_TOKEN not in caplog.text


# -- EmailNotifier ------------------------------------------------------------


class TestEmailNotifier:
    def make_notifier(self, **overrides):
        kwargs = dict(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
            use_tls=True,
            use_ssl=False,
        )
        kwargs.update(overrides)
        return EmailNotifier(**kwargs)

    @patch("wanwatcher.notifiers.email.smtplib.SMTP")
    def test_send_notification_via_starttls(self, mock_smtp):
        server = mock_smtp.return_value.__enter__.return_value
        notifier = self.make_notifier()
        assert notifier.send_notification(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )
        mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=30)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("user", "pass")
        server.send_message.assert_called_once()
        msg = server.send_message.call_args.args[0]
        assert msg["From"] == "from@example.com"
        assert msg["To"] == "to@example.com"
        assert "IP Address Changed" in msg["Subject"]

    @patch("wanwatcher.notifiers.email.smtplib.SMTP")
    def test_plain_connection_without_tls(self, mock_smtp):
        server = mock_smtp.return_value.__enter__.return_value
        notifier = self.make_notifier(use_tls=False, smtp_port=25)
        assert notifier.send_notification(
            CURRENT_IPS, {}, None, True, "Server", "2.0.0"
        )
        server.starttls.assert_not_called()

    @patch("wanwatcher.notifiers.email.smtplib.SMTP_SSL")
    def test_send_notification_via_ssl(self, mock_smtp_ssl):
        server = mock_smtp_ssl.return_value.__enter__.return_value
        notifier = self.make_notifier(use_ssl=True, use_tls=False, smtp_port=465)
        assert notifier.send_notification(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )
        mock_smtp_ssl.assert_called_once_with("smtp.example.com", 465, timeout=30)
        server.login.assert_called_once_with("user", "pass")
        server.send_message.assert_called_once()

    @patch("wanwatcher.notifiers.email.smtplib.SMTP")
    def test_smtp_failure_returns_false(self, mock_smtp):
        mock_smtp.return_value.__enter__.side_effect = ConnectionRefusedError()
        notifier = self.make_notifier()
        assert not notifier.send_notification(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )

    @patch("wanwatcher.notifiers.email.smtplib.SMTP")
    def test_send_update_notification(self, mock_smtp):
        server = mock_smtp.return_value.__enter__.return_value
        notifier = self.make_notifier()
        assert notifier.send_update_notification(UPDATE_INFO, "Server", "2.0.0")
        msg = server.send_message.call_args.args[0]
        assert "v2.1.0" in msg["Subject"]

    @patch("wanwatcher.notifiers.email.smtplib.SMTP")
    def test_send_event(self, mock_smtp):
        server = mock_smtp.return_value.__enter__.return_value
        notifier = self.make_notifier()
        assert notifier.send_event("Heartbeat", "Still alive", "Server")
        msg = server.send_message.call_args.args[0]
        assert "Heartbeat" in msg["Subject"]

    def test_string_recipients_are_split(self):
        notifier = self.make_notifier(to_addrs="a@example.com, b@example.com")
        assert notifier.to_addrs == ["a@example.com", "b@example.com"]


# -- AppriseNotifier (with a stubbed apprise module) ---------------------------


class _FakeAppriseInstance:
    def __init__(self):
        self.urls = []
        self.notify_calls = []
        self.notify_result = True
        self.add_result = True

    def add(self, url):
        if self.add_result:
            self.urls.append(url)
        return self.add_result

    def notify(self, title, body, notify_type):
        self.notify_calls.append({"title": title, "body": body, "type": notify_type})
        return self.notify_result


class _FakeNotifyType:
    INFO = "info-type"
    WARNING = "warning-type"
    FAILURE = "failure-type"


@pytest.fixture
def apprise_stub():
    stub = types.ModuleType("apprise")
    instance = _FakeAppriseInstance()
    stub.Apprise = lambda: instance
    stub.NotifyType = _FakeNotifyType
    saved = sys.modules.get("apprise")
    sys.modules["apprise"] = stub
    try:
        yield instance
    finally:
        if saved is None:
            sys.modules.pop("apprise", None)
        else:
            sys.modules["apprise"] = saved


class TestAppriseNotifier:
    def make_notifier(self, urls=None):
        from wanwatcher.notifiers.apprise import AppriseNotifier

        return AppriseNotifier(urls or ["ntfy://host/topic"])

    def test_urls_added_on_init(self, apprise_stub):
        self.make_notifier(["ntfy://host/topic", "pover://user@token"])
        assert apprise_stub.urls == ["ntfy://host/topic", "pover://user@token"]

    def test_rejected_url_logged_without_credentials(self, apprise_stub, caplog):
        apprise_stub.add_result = False
        with caplog.at_level("WARNING"):
            self.make_notifier(["ntfy://user:secret-pass@host/topic"])
        assert "secret-pass" not in caplog.text
        assert "ntfy" in caplog.text

    def test_send_notification_success(self, apprise_stub):
        notifier = self.make_notifier()
        assert notifier.send_notification(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )
        call = apprise_stub.notify_calls[0]
        assert call["type"] == _FakeNotifyType.INFO
        assert "9.9.9.9" in call["body"]

    def test_send_notification_failure(self, apprise_stub):
        apprise_stub.notify_result = False
        notifier = self.make_notifier()
        assert not notifier.send_notification(
            CURRENT_IPS, PREVIOUS_IPS, None, False, "Server", "2.0.0"
        )

    def test_send_update_notification(self, apprise_stub):
        notifier = self.make_notifier()
        assert notifier.send_update_notification(UPDATE_INFO, "Server", "2.0.0")
        assert "v2.1.0" in apprise_stub.notify_calls[0]["body"]

    @pytest.mark.parametrize(
        "severity,expected",
        [
            ("info", _FakeNotifyType.INFO),
            ("warning", _FakeNotifyType.WARNING),
            ("error", _FakeNotifyType.FAILURE),
            ("unknown", _FakeNotifyType.INFO),
        ],
    )
    def test_send_event_maps_severity(self, apprise_stub, severity, expected):
        notifier = self.make_notifier()
        assert notifier.send_event("Title", "Message", "Server", severity=severity)
        assert apprise_stub.notify_calls[0]["type"] == expected

    def test_import_error_without_package(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "apprise", None)
        from wanwatcher.notifiers.apprise import AppriseNotifier

        with pytest.raises(ImportError):
            AppriseNotifier(["ntfy://host/topic"])

    def test_build_manager_registers_apprise(self, apprise_stub):
        config = Config()
        config.apprise.enabled = True
        config.apprise.urls = ["ntfy://host/topic"]
        manager = build_manager(config)
        assert len(manager.providers) == 1
        assert manager.providers[0].name == "apprise"


# -- base provider ------------------------------------------------------------


class TestBaseProvider:
    def test_base_send_event_logs_and_succeeds(self, caplog):
        provider = NotificationProvider()
        with caplog.at_level("INFO"):
            assert provider.send_event("Title", "Message", "Server") is True
        assert "Title" in caplog.text

    def test_base_send_notification_is_abstract(self):
        provider = NotificationProvider()
        with pytest.raises(NotImplementedError):
            provider.send_notification({}, {}, None, True, "Server")
