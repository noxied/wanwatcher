"""
Unit tests for configuration validator
"""

import os
import pytest
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config_validator import ConfigValidator, ValidationError


class TestURLValidation:
    """Test URL validation"""

    def setup_method(self):
        self.validator = ConfigValidator()

    def test_valid_https_url(self):
        """Test valid HTTPS URL"""
        assert self.validator.validate_url(
            "https://discord.com/api/webhooks/123/abc",
            "TEST_URL"
        )
        assert len(self.validator.errors) == 0

    def test_valid_http_url_with_warning(self):
        """Test HTTP URL generates warning"""
        assert self.validator.validate_url(
            "http://example.com/webhook",
            "TEST_URL"
        )
        assert len(self.validator.warnings) > 0
        assert "non-HTTPS" in self.validator.warnings[0]

    def test_invalid_url_no_scheme(self):
        """Test URL without scheme"""
        assert not self.validator.validate_url(
            "discord.com/webhook",
            "TEST_URL"
        )
        assert len(self.validator.errors) > 0

    def test_invalid_url_no_domain(self):
        """Test URL without domain"""
        assert not self.validator.validate_url(
            "https://",
            "TEST_URL"
        )
        assert len(self.validator.errors) > 0

    def test_url_too_long(self):
        """Test URL exceeding max length"""
        long_url = "https://example.com/" + "a" * 2100
        assert not self.validator.validate_url(long_url, "TEST_URL")
        assert any("exceeds maximum length" in error for error in self.validator.errors)


class TestEmailValidation:
    """Test email validation"""

    def setup_method(self):
        self.validator = ConfigValidator()

    def test_valid_email(self):
        """Test valid email address"""
        assert self.validator.validate_email("user@example.com", "TEST_EMAIL")
        assert len(self.validator.errors) == 0

    def test_valid_email_with_plus(self):
        """Test email with plus sign"""
        assert self.validator.validate_email("user+tag@example.com", "TEST_EMAIL")

    def test_invalid_email_no_at(self):
        """Test email without @ symbol"""
        assert not self.validator.validate_email("userexample.com", "TEST_EMAIL")
        assert len(self.validator.errors) > 0

    def test_invalid_email_no_domain(self):
        """Test email without domain"""
        assert not self.validator.validate_email("user@", "TEST_EMAIL")
        assert len(self.validator.errors) > 0

    def test_invalid_email_no_tld(self):
        """Test email without TLD"""
        assert not self.validator.validate_email("user@example", "TEST_EMAIL")
        assert len(self.validator.errors) > 0


class TestPortValidation:
    """Test port validation"""

    def setup_method(self):
        self.validator = ConfigValidator()

    def test_valid_port(self):
        """Test valid port number"""
        assert self.validator.validate_port("587", "TEST_PORT")
        assert len(self.validator.errors) == 0

    def test_valid_port_range(self):
        """Test port at boundaries"""
        assert self.validator.validate_port("1", "TEST_PORT")
        assert self.validator.validate_port("65535", "TEST_PORT")

    def test_invalid_port_zero(self):
        """Test port 0"""
        assert not self.validator.validate_port("0", "TEST_PORT")
        assert len(self.validator.errors) > 0

    def test_invalid_port_too_high(self):
        """Test port above 65535"""
        assert not self.validator.validate_port("65536", "TEST_PORT")
        assert len(self.validator.errors) > 0

    def test_invalid_port_non_numeric(self):
        """Test non-numeric port"""
        assert not self.validator.validate_port("abc", "TEST_PORT")
        assert len(self.validator.errors) > 0


class TestIntervalValidation:
    """Test interval validation"""

    def setup_method(self):
        self.validator = ConfigValidator()

    def test_valid_interval(self):
        """Test valid interval"""
        assert self.validator.validate_interval("900", "TEST_INTERVAL", min_val=60)
        assert len(self.validator.errors) == 0

    def test_interval_at_minimum(self):
        """Test interval at minimum value"""
        assert self.validator.validate_interval("60", "TEST_INTERVAL", min_val=60)

    def test_invalid_interval_too_low(self):
        """Test interval below minimum"""
        assert not self.validator.validate_interval("30", "TEST_INTERVAL", min_val=60)
        assert len(self.validator.errors) > 0

    def test_invalid_interval_non_numeric(self):
        """Test non-numeric interval"""
        assert not self.validator.validate_interval("abc", "TEST_INTERVAL")
        assert len(self.validator.errors) > 0


class TestBooleanValidation:
    """Test boolean validation"""

    def setup_method(self):
        self.validator = ConfigValidator()

    def test_valid_true(self):
        """Test 'true' value"""
        assert self.validator.validate_boolean("true", "TEST_BOOL")
        assert len(self.validator.errors) == 0

    def test_valid_false(self):
        """Test 'false' value"""
        assert self.validator.validate_boolean("false", "TEST_BOOL")

    def test_case_insensitive(self):
        """Test case insensitivity"""
        assert self.validator.validate_boolean("TRUE", "TEST_BOOL")
        assert self.validator.validate_boolean("False", "TEST_BOOL")

    def test_invalid_value(self):
        """Test invalid boolean value"""
        assert not self.validator.validate_boolean("yes", "TEST_BOOL")
        assert len(self.validator.errors) > 0


class TestTelegramValidation:
    """Test Telegram-specific validation"""

    def setup_method(self):
        self.validator = ConfigValidator()

    def test_valid_telegram_token(self):
        """Test valid Telegram bot token"""
        assert self.validator.validate_telegram_token("123456789:ABCdefGHIjklMNOpqrsTUVwxyz_123")

    def test_invalid_telegram_token_format(self):
        """Test invalid token format"""
        assert not self.validator.validate_telegram_token("invalid_token")
        assert len(self.validator.errors) > 0

    def test_valid_numeric_chat_id(self):
        """Test valid numeric chat ID"""
        assert self.validator.validate_telegram_chat_id("123456789")

    def test_valid_username_chat_id(self):
        """Test valid username chat ID"""
        assert self.validator.validate_telegram_chat_id("@username")

    def test_invalid_chat_id(self):
        """Test invalid chat ID"""
        assert not self.validator.validate_telegram_chat_id("invalid")
        assert len(self.validator.errors) > 0


class TestDiscordConfig:
    """Test Discord configuration validation"""

    def setup_method(self):
        self.validator = ConfigValidator()

    def test_valid_discord_config(self):
        """Test valid Discord configuration"""
        assert self.validator.validate_discord_config(
            "true",
            "https://discord.com/api/webhooks/123/abc",
            ""
        )
        assert len(self.validator.errors) == 0

    def test_discord_enabled_no_webhook(self):
        """Test Discord enabled without webhook URL"""
        assert not self.validator.validate_discord_config("true", "", "")
        assert any("DISCORD_WEBHOOK_URL" in error for error in self.validator.errors)

    def test_discord_disabled(self):
        """Test Discord disabled"""
        assert self.validator.validate_discord_config("false", "", "")
        assert len(self.validator.errors) == 0


class TestEmailConfig:
    """Test Email configuration validation"""

    def setup_method(self):
        self.validator = ConfigValidator()

    def test_valid_email_config(self):
        """Test valid email configuration"""
        assert self.validator.validate_email_config(
            "true",
            "smtp.gmail.com",
            "587",
            "user@example.com",
            "password123",
            "from@example.com",
            "to@example.com",
            "true",
            "false"
        )
        assert len(self.validator.errors) == 0

    def test_email_enabled_missing_host(self):
        """Test email enabled without SMTP host"""
        assert not self.validator.validate_email_config(
            "true", "", "587", "user", "pass", "from", "to", "true", "false"
        )
        assert any("EMAIL_SMTP_HOST" in error for error in self.validator.errors)

    def test_conflicting_tls_ssl(self):
        """Test conflicting TLS and SSL settings"""
        assert not self.validator.validate_email_config(
            "true",
            "smtp.gmail.com",
            "587",
            "user@example.com",
            "password",
            "from@example.com",
            "to@example.com",
            "true",
            "true"
        )
        assert any("TLS and EMAIL_USE_SSL" in error for error in self.validator.errors)


class TestGeneralConfig:
    """Test general configuration validation"""

    def setup_method(self):
        self.validator = ConfigValidator()

    def test_valid_general_config(self):
        """Test valid general configuration"""
        assert self.validator.validate_general_config("900", "true", "true")
        assert len(self.validator.errors) == 0

    def test_short_interval_warning(self):
        """Test warning for short check interval"""
        self.validator.validate_general_config("120", "true", "false")
        assert any("less than 5 minutes" in warning for warning in self.validator.warnings)

    def test_both_protocols_disabled(self):
        """Test error when both protocols disabled"""
        assert not self.validator.validate_general_config("900", "false", "false")
        assert any("Both MONITOR_IPV4 and MONITOR_IPV6" in error for error in self.validator.errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
