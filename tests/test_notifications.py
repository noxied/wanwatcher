"""
Unit tests for notification system
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from notifications import retry_with_backoff, NotificationManager, DiscordNotifier


class TestRetryLogic:
    """Test retry with backoff functionality"""

    def test_success_on_first_try(self):
        """Test function succeeds on first attempt"""
        mock_func = Mock(return_value=True)

        result = retry_with_backoff(mock_func, max_retries=3, base_delay=0.1)

        assert result is True
        assert mock_func.call_count == 1

    def test_success_on_second_try(self):
        """Test function succeeds on second attempt"""
        mock_func = Mock(side_effect=[False, True])

        result = retry_with_backoff(mock_func, max_retries=3, base_delay=0.1)

        assert result is True
        assert mock_func.call_count == 2

    def test_failure_after_all_retries(self):
        """Test function fails after all retries"""
        mock_func = Mock(return_value=False)

        result = retry_with_backoff(mock_func, max_retries=3, base_delay=0.1)

        assert result is False
        assert mock_func.call_count == 3

    def test_exception_with_retry(self):
        """Test exception handling with retry"""
        mock_func = Mock(side_effect=[
            Exception("First attempt failed"),
            Exception("Second attempt failed"),
            True
        ])

        result = retry_with_backoff(mock_func, max_retries=3, base_delay=0.1)

        assert result is True
        assert mock_func.call_count == 3

    def test_all_retries_fail_with_exception(self):
        """Test all retries fail with exceptions"""
        mock_func = Mock(side_effect=Exception("Always fails"))

        result = retry_with_backoff(mock_func, max_retries=3, base_delay=0.1)

        assert result is False
        assert mock_func.call_count == 3

    def test_exponential_backoff_timing(self):
        """Test that backoff delay increases exponentially"""
        call_times = []

        def time_tracking_func():
            call_times.append(time.time())
            return False

        retry_with_backoff(time_tracking_func, max_retries=3, base_delay=0.1)

        # Check that delays increase (approximately)
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            # Second delay should be roughly double the first
            assert delay2 > delay1


class TestNotificationManager:
    """Test notification manager"""

    def test_add_provider(self):
        """Test adding notification provider"""
        manager = NotificationManager()
        mock_provider = Mock()

        manager.add_provider(mock_provider)

        assert len(manager.providers) == 1
        assert manager.providers[0] == mock_provider

    def test_send_to_all_empty(self):
        """Test sending with no providers"""
        manager = NotificationManager()

        result = manager.send_to_all(
            {'ipv4': '1.1.1.1', 'ipv6': None},
            {'ipv4': None, 'ipv6': None},
            None,
            True,
            "Test Server",
            "1.4.0"
        )

        assert result == {}

    @patch('notifications.retry_with_backoff')
    def test_send_to_all_with_provider(self, mock_retry):
        """Test sending with single provider"""
        mock_retry.return_value = True

        manager = NotificationManager()
        mock_provider = Mock()
        mock_provider.__class__.__name__ = "TestProvider"
        mock_provider.send_notification = Mock(return_value=True)

        manager.add_provider(mock_provider)

        result = manager.send_to_all(
            {'ipv4': '1.1.1.1', 'ipv6': None},
            {'ipv4': None, 'ipv6': None},
            None,
            True,
            "Test Server",
            "1.4.0"
        )

        assert "TestProvider" in result
        assert mock_retry.called

    @patch('notifications.retry_with_backoff')
    def test_send_to_all_multiple_providers(self, mock_retry):
        """Test sending with multiple providers"""
        mock_retry.return_value = True

        manager = NotificationManager()

        provider1 = Mock()
        provider1.__class__.__name__ = "Provider1"
        provider2 = Mock()
        provider2.__class__.__name__ = "Provider2"

        manager.add_provider(provider1)
        manager.add_provider(provider2)

        result = manager.send_to_all(
            {'ipv4': '1.1.1.1', 'ipv6': None},
            {'ipv4': None, 'ipv6': None},
            None,
            False,
            "Test Server",
            "1.4.0"
        )

        assert len(result) == 2
        assert "Provider1" in result
        assert "Provider2" in result


class TestDiscordNotifier:
    """Test Discord notification provider"""

    def test_discord_notifier_initialization(self):
        """Test Discord notifier initialization"""
        notifier = DiscordNotifier(
            "https://discord.com/api/webhooks/123/abc",
            "TestBot",
            ""
        )

        assert notifier.webhook_url == "https://discord.com/api/webhooks/123/abc"
        assert notifier.bot_name == "TestBot"

    def test_discord_avatar_url_custom(self):
        """Test custom avatar URL"""
        notifier = DiscordNotifier(
            "https://discord.com/api/webhooks/123/abc",
            "TestBot",
            "https://example.com/avatar.png"
        )

        assert notifier._get_avatar_url() == "https://example.com/avatar.png"

    def test_discord_avatar_url_default(self):
        """Test default avatar (empty string)"""
        notifier = DiscordNotifier(
            "https://discord.com/api/webhooks/123/abc",
            "TestBot",
            ""
        )

        assert notifier._get_avatar_url() == ""

    @patch('notifications.requests.post')
    def test_discord_send_success(self, mock_post):
        """Test successful Discord notification"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        notifier = DiscordNotifier(
            "https://discord.com/api/webhooks/123/abc",
            "TestBot"
        )

        result = notifier.send_notification(
            {'ipv4': '1.1.1.1', 'ipv6': None},
            {'ipv4': None, 'ipv6': None},
            None,
            True,
            "Test Server",
            "1.4.0"
        )

        assert result is True
        assert mock_post.called

    @patch('notifications.requests.post')
    def test_discord_send_failure(self, mock_post):
        """Test failed Discord notification"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        notifier = DiscordNotifier(
            "https://discord.com/api/webhooks/123/abc",
            "TestBot"
        )

        result = notifier.send_notification(
            {'ipv4': '1.1.1.1', 'ipv6': None},
            {'ipv4': None, 'ipv6': None},
            None,
            True,
            "Test Server",
            "1.4.0"
        )

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
