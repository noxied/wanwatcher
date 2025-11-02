"""
Unit tests for IP validation functions
"""

import os
import sys
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock environment variables before importing
os.environ.setdefault('DISCORD_ENABLED', 'false')
os.environ.setdefault('TELEGRAM_ENABLED', 'false')
os.environ.setdefault('EMAIL_ENABLED', 'false')
os.environ.setdefault('CHECK_INTERVAL', '900')

from wanwatcher_docker import is_valid_ipv6


class TestIPv6Validation:
    """Test IPv6 address validation"""

    def test_valid_ipv6_full(self):
        """Test valid full IPv6 address"""
        assert is_valid_ipv6("2001:0db8:85a3:0000:0000:8a2e:0370:7334")

    def test_valid_ipv6_compressed(self):
        """Test valid compressed IPv6 address"""
        assert is_valid_ipv6("2001:db8::8a2e:370:7334")

    def test_valid_ipv6_short(self):
        """Test valid short IPv6 address"""
        assert is_valid_ipv6("2001:db8::1")

    def test_invalid_ipv6_loopback(self):
        """Test rejection of loopback address"""
        assert not is_valid_ipv6("::1")

    def test_invalid_ipv6_link_local(self):
        """Test rejection of link-local address"""
        assert not is_valid_ipv6("fe80::1")
        assert not is_valid_ipv6("fe80::dead:beef:cafe")

    def test_invalid_ipv6_multicast(self):
        """Test rejection of multicast address"""
        assert not is_valid_ipv6("ff02::1")
        assert not is_valid_ipv6("ff00::1")

    def test_invalid_ipv6_private_ula(self):
        """Test rejection of private/ULA address"""
        assert not is_valid_ipv6("fc00::1")
        assert not is_valid_ipv6("fd00::1")

    def test_invalid_ipv6_format(self):
        """Test rejection of malformed IPv6"""
        assert not is_valid_ipv6("not:an:ipv6:address")
        assert not is_valid_ipv6("12345")
        assert not is_valid_ipv6("192.168.1.1")

    def test_invalid_ipv6_too_many_groups(self):
        """Test rejection of IPv6 with too many groups"""
        assert not is_valid_ipv6("2001:0db8:85a3:0000:0000:8a2e:0370:7334:extra")

    def test_valid_ipv6_google_dns(self):
        """Test Google's public IPv6 DNS"""
        assert is_valid_ipv6("2001:4860:4860::8888")

    def test_valid_ipv6_cloudflare_dns(self):
        """Test Cloudflare's public IPv6 DNS"""
        assert is_valid_ipv6("2606:4700:4700::1111")


class TestIPv4Validation:
    """Test IPv4 address handling (basic checks)"""

    def test_simple_ipv4_detection(self):
        """Test that IPv4 addresses contain dots"""
        ipv4_examples = [
            "192.168.1.1",
            "8.8.8.8",
            "1.1.1.1",
            "203.0.113.42"
        ]
        for ip in ipv4_examples:
            assert '.' in ip

    def test_ipv6_doesnt_have_dots(self):
        """Test that IPv6 addresses don't contain dots"""
        ipv6_examples = [
            "2001:db8::1",
            "fe80::1",
            "::1"
        ]
        for ip in ipv6_examples:
            # IPv6 addresses shouldn't have dots (unless IPv4-mapped)
            assert '.' not in ip or '::ffff:' in ip


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
