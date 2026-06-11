"""Tests for wanwatcher.detector: parsing, validation, rotation, confirmation."""

from unittest.mock import Mock, patch

import pytest
import requests

from wanwatcher.detector import (
    IPV4_SOURCES,
    IPV6_SOURCES,
    IPDetector,
    is_valid_ipv4,
    is_valid_ipv6,
)

PUBLIC_V4_A = "8.8.8.8"
PUBLIC_V4_B = "9.9.9.9"
PUBLIC_V4_C = "93.184.216.34"
PUBLIC_V6 = "2606:4700:4700::1111"


def make_response(text="", json_data=None, status=200):
    response = Mock()
    response.text = text
    response.status_code = status
    if json_data is not None:
        response.json.return_value = json_data
    else:
        response.json.side_effect = ValueError("not json")
    response.raise_for_status.return_value = None
    return response


class TestIsValidIPv4:
    @pytest.mark.parametrize("ip", [PUBLIC_V4_A, "1.1.1.1", PUBLIC_V4_C])
    def test_global_addresses_accepted(self, ip):
        assert is_valid_ipv4(ip)

    @pytest.mark.parametrize(
        "ip",
        [
            "10.0.0.1",  # private
            "172.16.0.1",  # private
            "192.168.1.1",  # private
            "127.0.0.1",  # loopback
            "169.254.1.1",  # link-local
            "224.0.0.1",  # multicast
            "240.0.0.1",  # reserved
            "0.0.0.0",  # unspecified
        ],
    )
    def test_special_use_addresses_rejected(self, ip):
        assert not is_valid_ipv4(ip)

    @pytest.mark.parametrize("ip", ["256.1.1.1", "not-an-ip", "", "1.2.3", PUBLIC_V6])
    def test_malformed_addresses_rejected(self, ip):
        assert not is_valid_ipv4(ip)


class TestIsValidIPv6:
    @pytest.mark.parametrize(
        "ip",
        [
            "2001:4860:4860:0000:0000:0000:0000:8888",
            "2001:4860:4860::8888",
            "2606:4700:4700::1111",
            "2606:4700:4700::1001",
        ],
    )
    def test_global_addresses_accepted(self, ip):
        assert is_valid_ipv6(ip)

    def test_loopback_rejected(self):
        assert not is_valid_ipv6("::1")

    def test_link_local_rejected(self):
        assert not is_valid_ipv6("fe80::1")
        assert not is_valid_ipv6("fe80::dead:beef:cafe")

    def test_multicast_rejected(self):
        assert not is_valid_ipv6("ff02::1")
        assert not is_valid_ipv6("ff00::1")

    def test_private_ula_rejected(self):
        assert not is_valid_ipv6("fc00::1")
        assert not is_valid_ipv6("fd00::1")

    @pytest.mark.parametrize(
        "ip",
        [
            "not:an:ipv6:address",
            "12345",
            "192.168.1.1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334:extra",
        ],
    )
    def test_malformed_addresses_rejected(self, ip):
        assert not is_valid_ipv6(ip)


@patch("wanwatcher.detector.requests.get")
class TestResponseParsing:
    def test_json_source(self, mock_get):
        mock_get.return_value = make_response(json_data={"ip": PUBLIC_V4_A})
        detector = IPDetector()
        assert detector.get_ipv4() == PUBLIC_V4_A
        assert mock_get.call_args[0][0] == IPV4_SOURCES[0].url

    def test_cloudflare_trace_source(self, mock_get):
        trace = f"fl=123\nh=1.1.1.1\nip={PUBLIC_V4_A}\nts=0\n"
        mock_get.return_value = make_response(text=trace)
        detector = IPDetector()
        detector._ipv4_offset = 1  # cloudflare trace source first
        assert detector.get_ipv4() == PUBLIC_V4_A

    def test_plain_text_source(self, mock_get):
        mock_get.return_value = make_response(text=f"  {PUBLIC_V4_A}\n")
        detector = IPDetector()
        detector._ipv4_offset = 2  # icanhazip (plain) first
        assert detector.get_ipv4() == PUBLIC_V4_A

    def test_ipv6_json_source(self, mock_get):
        mock_get.return_value = make_response(json_data={"ip": PUBLIC_V6})
        detector = IPDetector()
        assert detector.get_ipv6() == PUBLIC_V6

    def test_json_missing_key_falls_through(self, mock_get):
        responses = [
            make_response(json_data={"address": PUBLIC_V4_A}),  # wrong key
            make_response(text=f"ip={PUBLIC_V4_B}"),  # cloudflare trace
        ]
        mock_get.side_effect = responses
        detector = IPDetector()
        assert detector.get_ipv4() == PUBLIC_V4_B


@patch("wanwatcher.detector.requests.get")
class TestAddressRejection:
    def test_private_ipv4_is_skipped_and_next_source_used(self, mock_get):
        mock_get.side_effect = [
            make_response(json_data={"ip": "192.168.1.1"}),
            make_response(text=f"ip={PUBLIC_V4_A}"),
        ]
        detector = IPDetector()
        assert detector.get_ipv4() == PUBLIC_V4_A
        assert mock_get.call_count == 2

    def test_link_local_ipv6_is_rejected(self, mock_get):
        mock_get.return_value = make_response(json_data={"ip": "fe80::1"})
        detector = IPDetector()
        assert detector.get_ipv6() is None
        assert mock_get.call_count == len(IPV6_SOURCES)

    def test_all_sources_returning_garbage_yields_none(self, mock_get):
        mock_get.return_value = make_response(text="<html>error page</html>")
        detector = IPDetector()
        assert detector.get_ipv4() is None
        assert mock_get.call_count == len(IPV4_SOURCES)


@patch("wanwatcher.detector.requests.get")
class TestRotation:
    def test_offset_advances_between_calls(self, mock_get):
        mock_get.return_value = make_response(json_data={"ip": PUBLIC_V4_A})
        # All sources happen to return the JSON body; the parser of the
        # plain sources would strip the repr text, so give them valid text.
        mock_get.return_value.text = PUBLIC_V4_A
        detector = IPDetector()

        detector.get_ipv4()
        detector.get_ipv4()
        detector.get_ipv4()

        urls = [call.args[0] for call in mock_get.call_args_list]
        assert urls[0] == IPV4_SOURCES[0].url
        assert urls[1] == IPV4_SOURCES[1].url
        assert urls[2] == IPV4_SOURCES[2].url

    def test_offset_wraps_around(self, mock_get):
        mock_get.return_value = make_response(
            text=PUBLIC_V4_A, json_data={"ip": PUBLIC_V4_A}
        )
        detector = IPDetector()
        for _ in range(len(IPV4_SOURCES) + 1):
            detector.get_ipv4()
        urls = [call.args[0] for call in mock_get.call_args_list]
        assert urls[-1] == IPV4_SOURCES[0].url


@patch("wanwatcher.detector.requests.get")
class TestChangeConfirmation:
    def _dispatch(self, mapping):
        """Build a side_effect returning canned responses per URL."""

        def side_effect(url, timeout=None):
            result = mapping[url]
            if isinstance(result, Exception):
                raise result
            return result

        return side_effect

    def test_unchanged_value_needs_no_confirmation(self, mock_get):
        mock_get.return_value = make_response(json_data={"ip": PUBLIC_V4_A})
        detector = IPDetector()
        assert detector.get_ipv4(previous=PUBLIC_V4_A) == PUBLIC_V4_A
        assert mock_get.call_count == 1

    def test_changed_value_confirmed_by_second_source(self, mock_get):
        mock_get.side_effect = self._dispatch(
            {
                IPV4_SOURCES[0].url: make_response(json_data={"ip": PUBLIC_V4_B}),
                IPV4_SOURCES[1].url: make_response(text=f"ip={PUBLIC_V4_B}"),
            }
        )
        detector = IPDetector()
        assert detector.get_ipv4(previous=PUBLIC_V4_A) == PUBLIC_V4_B
        assert mock_get.call_count == 2

    def test_source_disagreement_keeps_previous(self, mock_get):
        mock_get.side_effect = self._dispatch(
            {
                IPV4_SOURCES[0].url: make_response(json_data={"ip": PUBLIC_V4_B}),
                IPV4_SOURCES[1].url: make_response(text=f"ip={PUBLIC_V4_C}"),
            }
        )
        detector = IPDetector()
        assert detector.get_ipv4(previous=PUBLIC_V4_A) == PUBLIC_V4_A
        assert mock_get.call_count == 2

    def test_single_source_fallback_when_others_unreachable(self, mock_get):
        mapping = {
            source.url: requests.exceptions.ConnectionError("down")
            for source in IPV4_SOURCES
        }
        mapping[IPV4_SOURCES[0].url] = make_response(json_data={"ip": PUBLIC_V4_B})
        mock_get.side_effect = self._dispatch(mapping)
        detector = IPDetector()
        assert detector.get_ipv4(previous=PUBLIC_V4_A) == PUBLIC_V4_B
        assert mock_get.call_count == len(IPV4_SOURCES)

    def test_confirmation_disabled_accepts_first_answer(self, mock_get):
        mock_get.return_value = make_response(json_data={"ip": PUBLIC_V4_B})
        detector = IPDetector(change_confirmation=False)
        assert detector.get_ipv4(previous=PUBLIC_V4_A) == PUBLIC_V4_B
        assert mock_get.call_count == 1

    def test_first_detection_skips_confirmation(self, mock_get):
        mock_get.return_value = make_response(json_data={"ip": PUBLIC_V4_B})
        detector = IPDetector()
        assert detector.get_ipv4(previous=None) == PUBLIC_V4_B
        assert mock_get.call_count == 1


@patch("wanwatcher.detector.requests.get")
class TestFailureModes:
    def test_all_sources_failing_returns_none(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("offline")
        detector = IPDetector()
        assert detector.get_ipv4() is None
        assert detector.get_ipv6() is None

    def test_http_error_is_handled(self, mock_get):
        response = make_response(text="oops", status=503)
        response.raise_for_status.side_effect = requests.exceptions.HTTPError("503")
        mock_get.return_value = response
        detector = IPDetector()
        assert detector.get_ipv4() is None

    def test_timeout_is_handled(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("timed out")
        detector = IPDetector()
        assert detector.get_ipv4() is None
