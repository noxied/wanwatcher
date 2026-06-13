"""Security tests: untrusted strings must be escaped in notification bodies.

Geo fields (org/city/region/timezone) come from ipinfo.io and the changelog
comes from GitHub release notes. They must not inject markup into HTML email,
Telegram HTML, or Discord markdown. For Telegram, escaping also prevents the
400 "can't parse entities" error that would silently drop a real alert.
"""

from email.message import Message
from unittest.mock import Mock, patch

import pytest

from wanwatcher.notifiers import DiscordNotifier, EmailNotifier, TelegramNotifier
from wanwatcher.notifiers._escape import (
    discord_escape,
    html_escape,
    telegram_escape,
)

BOT_TOKEN = "123456789:SECRETtokenSECRETtokenSECRETtoken"

CURRENT = {"ipv4": "1.2.3.4", "ipv6": None}
PREVIOUS = {"ipv4": "0.0.0.0", "ipv6": None}

# org carries HTML, an ampersand, and a markdown link - the three attack shapes.
HOSTILE_GEO = {
    "org": "Evil <b>ISP</b> & [click](http://attacker.example)",
    "city": "City<script>",
    "region": None,
    "country": "US",
    "timezone": "Zone&<x>",
}
HOSTILE_UPDATE = {
    "current_version": "2.3.0",
    "latest_version": "2.4.0",
    "release_name": "v2.4.0",
    "release_url": "https://github.com/noxied/wanwatcher/releases/tag/v2.4.0",
    "release_body": "- Normal fix\n- <script>alert(1)</script> & [x](http://evil)",
    "published_at": "2026-06-13T00:00:00Z",
}


# -- the escape helpers -------------------------------------------------------


def test_html_escape_neutralises_markup():
    out = html_escape('<b>x</b> & "q"')
    assert "<b>" not in out
    assert "&lt;b&gt;" in out and "&amp;" in out and "&quot;" in out


def test_html_escape_handles_none():
    assert html_escape(None) == ""


def test_telegram_escape_only_html_specials():
    out = telegram_escape("a <b> & c >")
    assert out == "a &lt;b&gt; &amp; c &gt;"


def test_discord_escape_neutralises_link_and_formatting():
    out = discord_escape("[click](http://evil) *bold* `code`")
    assert "[click](http://evil)" not in out
    assert "\\[click\\]\\(http://evil\\)" in out
    assert "\\*bold\\*" in out


# -- Discord ------------------------------------------------------------------


@patch("wanwatcher.notifiers.discord.requests.post")
class TestDiscordEscaping:
    def make(self):
        return DiscordNotifier("https://discord.com/api/webhooks/1/a")

    def test_geo_markdown_is_escaped_in_field_value(self, mock_post):
        mock_post.return_value = Mock(status_code=204)
        assert self.make().send_notification(
            CURRENT, PREVIOUS, HOSTILE_GEO, False, "Srv", "2.4.0"
        )
        fields = mock_post.call_args.kwargs["json"]["embeds"][0]["fields"]
        geo = next(f["value"] for f in fields if "Location" in f["name"])
        # The markdown link syntax must not survive intact.
        assert "[click](http://attacker.example)" not in geo
        assert "\\[click\\]" in geo

    def test_server_name_escaped_in_description(self, mock_post):
        mock_post.return_value = Mock(status_code=204)
        self.make().send_notification(CURRENT, {}, None, True, "Srv *evil*", "2.4.0")
        desc = mock_post.call_args.kwargs["json"]["embeds"][0]["description"]
        assert "*evil*" not in desc
        assert "\\*evil\\*" in desc

    def test_changelog_escaped(self, mock_post):
        mock_post.return_value = Mock(status_code=204)
        self.make().send_update_notification(HOSTILE_UPDATE, "Srv", "2.4.0")
        fields = mock_post.call_args.kwargs["json"]["embeds"][0]["fields"]
        whats_new = next(f["value"] for f in fields if "What's New" in f["name"])
        assert "[x](http://evil)" not in whats_new


# -- Telegram -----------------------------------------------------------------


@patch("wanwatcher.notifiers.telegram.requests.post")
class TestTelegramEscaping:
    def make(self):
        return TelegramNotifier(BOT_TOKEN, "424242", parse_mode="HTML")

    def test_geo_html_is_escaped(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        assert self.make().send_notification(
            CURRENT, PREVIOUS, HOSTILE_GEO, False, "Srv", "2.4.0"
        )
        text = mock_post.call_args.kwargs["json"]["text"]
        # Raw hostile markup absent; escaped form present.
        assert "<script>" not in text
        assert "Evil <b>ISP</b>" not in text
        assert "&lt;script&gt;" in text
        assert "&lt;b&gt;ISP&lt;/b&gt;" in text

    def test_server_name_escaped(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        self.make().send_notification(CURRENT, {}, None, True, "S<b>X", "2.4.0")
        text = mock_post.call_args.kwargs["json"]["text"]
        assert "S<b>X" not in text
        assert "S&lt;b&gt;X" in text

    def test_changelog_and_url_escaped(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        self.make().send_update_notification(HOSTILE_UPDATE, "Srv", "2.4.0")
        text = mock_post.call_args.kwargs["json"]["text"]
        assert "<script>" not in text
        assert "&lt;script&gt;" in text

    def test_event_message_escaped(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        self.make().send_event("T<i>", "M & <b>", "S<x>")
        text = mock_post.call_args.kwargs["json"]["text"]
        assert "T<i>" not in text and "M & <b>" not in text
        assert "&lt;i&gt;" in text and "&amp;" in text

    def test_template_tags_survive(self, mock_post):
        # The intentional formatting tags must still be present (escaping only
        # hits the data, not the template).
        mock_post.return_value = Mock(status_code=200)
        self.make().send_notification(CURRENT, {}, None, True, "Srv", "2.4.0")
        text = mock_post.call_args.kwargs["json"]["text"]
        assert "<b>" in text  # template bold still there


# -- Email --------------------------------------------------------------------


def _html_part(msg: Message) -> str:
    for part in msg.get_payload():
        if part.get_content_type() == "text/html":
            return part.get_payload(decode=True).decode("utf-8")
    raise AssertionError("no HTML part found")


def _text_part(msg: Message) -> str:
    for part in msg.get_payload():
        if part.get_content_type() == "text/plain":
            return part.get_payload(decode=True).decode("utf-8")
    raise AssertionError("no text part found")


class TestEmailEscaping:
    def make(self):
        return EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
        )

    @patch("wanwatcher.notifiers.email.smtplib.SMTP")
    def test_geo_escaped_in_html(self, mock_smtp):
        server = mock_smtp.return_value.__enter__.return_value
        assert self.make().send_notification(
            CURRENT, PREVIOUS, HOSTILE_GEO, False, "Srv", "2.4.0"
        )
        html = _html_part(server.send_message.call_args.args[0])
        assert "<script>" not in html
        assert "Evil <b>ISP</b>" not in html
        assert "&lt;script&gt;" in html
        assert "&lt;b&gt;ISP&lt;/b&gt;" in html

    @patch("wanwatcher.notifiers.email.smtplib.SMTP")
    def test_html_template_structure_survives(self, mock_smtp):
        server = mock_smtp.return_value.__enter__.return_value
        self.make().send_notification(CURRENT, PREVIOUS, HOSTILE_GEO, False, "S", "2")
        html = _html_part(server.send_message.call_args.args[0])
        assert "<table" in html and "<body" in html  # template tags intact

    @patch("wanwatcher.notifiers.email.smtplib.SMTP")
    def test_changelog_and_url_escaped_in_update_html(self, mock_smtp):
        server = mock_smtp.return_value.__enter__.return_value
        self.make().send_update_notification(HOSTILE_UPDATE, "Srv", "2.4.0")
        html = _html_part(server.send_message.call_args.args[0])
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    @patch("wanwatcher.notifiers.email.smtplib.SMTP")
    def test_event_escaped_in_html(self, mock_smtp):
        server = mock_smtp.return_value.__enter__.return_value
        self.make().send_event("T<x>", "M & <b>bad</b>", "S")
        html = _html_part(server.send_message.call_args.args[0])
        assert "<b>bad</b>" not in html
        assert "&lt;b&gt;bad&lt;/b&gt;" in html

    @patch("wanwatcher.notifiers.email.smtplib.SMTP")
    def test_plain_text_part_is_not_html_escaped(self, mock_smtp):
        # The plain-text alternative is not an HTML context; it should carry the
        # raw value (no entity noise).
        server = mock_smtp.return_value.__enter__.return_value
        self.make().send_notification(
            CURRENT, PREVIOUS, HOSTILE_GEO, False, "Srv", "2.4.0"
        )
        text = _text_part(server.send_message.call_args.args[0])
        assert "Evil <b>ISP</b> &" in text  # raw, unescaped in plain text
