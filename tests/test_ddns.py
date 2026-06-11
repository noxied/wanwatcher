"""Tests for the DDNS provider clients."""

from unittest.mock import MagicMock, patch

from wanwatcher.config import (
    CloudflareConfig,
    DDNSConfig,
    DuckDNSConfig,
    DynDNS2Config,
)
from wanwatcher.ddns import build_ddns_client
from wanwatcher.ddns.cloudflare import CloudflareClient
from wanwatcher.ddns.duckdns import DuckDNSClient
from wanwatcher.ddns.dyndns2 import DynDNS2Client
from wanwatcher.metrics import Metrics

# -- builder ----------------------------------------------------------------


def test_build_unknown_provider_returns_none():
    cfg = DDNSConfig(enabled=True, provider="bogus")
    assert build_ddns_client(cfg) is None


def test_build_duckdns_missing_fields_returns_none():
    cfg = DDNSConfig(
        enabled=True, provider="duckdns", duckdns=DuckDNSConfig(token="", domains=[])
    )
    assert build_ddns_client(cfg) is None


def test_build_duckdns_ok():
    cfg = DDNSConfig(
        enabled=True,
        provider="duckdns",
        duckdns=DuckDNSConfig(token="t", domains=["home"]),
    )
    assert isinstance(build_ddns_client(cfg), DuckDNSClient)


# -- DuckDNS ----------------------------------------------------------------


def _duck(domains):
    return DuckDNSClient(DuckDNSConfig(token="secret", domains=domains))


@patch("wanwatcher.ddns.duckdns.requests.get")
def test_duckdns_ok(mock_get):
    mock_get.return_value = MagicMock(ok=True, status_code=200, text="OK")
    client = _duck(["home"])
    result = client.update("1.2.3.4", None)
    assert result == {"home": True}


@patch("wanwatcher.ddns.duckdns.requests.get")
def test_duckdns_ko_marks_failure(mock_get):
    mock_get.return_value = MagicMock(ok=True, status_code=200, text="KO")
    client = _duck(["home"])
    assert client.update("1.2.3.4", None) == {"home": False}


@patch("wanwatcher.ddns.duckdns.requests.get")
def test_duckdns_strips_suffix(mock_get):
    mock_get.return_value = MagicMock(ok=True, status_code=200, text="OK")
    client = _duck(["home.duckdns.org"])
    client.update("1.2.3.4", None)
    assert mock_get.call_args.kwargs["params"]["domains"] == "home"


# -- dyndns2 ----------------------------------------------------------------


def _dyn(hostnames, server="https://dynupdate.no-ip.com"):
    return DynDNS2Client(
        DynDNS2Config(server=server, username="u", password="p", hostnames=hostnames)
    )


@patch("wanwatcher.ddns.dyndns2.requests.get")
def test_dyndns2_good(mock_get):
    mock_get.return_value = MagicMock(status_code=200, text="good 1.2.3.4")
    client = _dyn(["host.example.com"])
    assert client.update("1.2.3.4", None) == {"host.example.com": True}


@patch("wanwatcher.ddns.dyndns2.requests.get")
def test_dyndns2_nochg_is_success(mock_get):
    mock_get.return_value = MagicMock(status_code=200, text="nochg 1.2.3.4")
    client = _dyn(["host.example.com"])
    assert client.update("1.2.3.4", None) == {"host.example.com": True}


@patch("wanwatcher.ddns.dyndns2.requests.get")
def test_dyndns2_badauth_fails(mock_get):
    mock_get.return_value = MagicMock(status_code=200, text="badauth")
    client = _dyn(["host.example.com"])
    assert client.update("1.2.3.4", None) == {"host.example.com": False}


@patch("wanwatcher.ddns.dyndns2.requests.get")
def test_dyndns2_sends_user_agent(mock_get):
    mock_get.return_value = MagicMock(status_code=200, text="good")
    client = _dyn(["host.example.com"])
    client.update("1.2.3.4", None)
    assert "WANwatcher" in mock_get.call_args.kwargs["headers"]["User-Agent"]


@patch("wanwatcher.ddns.dyndns2.requests.get")
def test_dyndns2_dual_stack_comma_joined(mock_get):
    mock_get.return_value = MagicMock(status_code=200, text="good")
    client = _dyn(["host.example.com"])
    client.update("1.2.3.4", "2001:db8::1")
    assert mock_get.call_args.kwargs["params"]["myip"] == "1.2.3.4,2001:db8::1"


def test_dyndns2_forces_https():
    client = _dyn(["h"], server="http://dynupdate.no-ip.com")
    assert client.server.startswith("https://")


# -- base class behavior ----------------------------------------------------


@patch("wanwatcher.ddns.duckdns.requests.get")
def test_noop_when_unchanged(mock_get):
    mock_get.return_value = MagicMock(ok=True, status_code=200, text="OK")
    metrics = Metrics()
    client = DuckDNSClient(DuckDNSConfig(token="t", domains=["home"]), metrics=metrics)
    client.update("1.2.3.4", None)
    assert mock_get.call_count == 1
    # Second call with the same address must not hit the network.
    client.update("1.2.3.4", None)
    assert mock_get.call_count == 1
    assert 'result="noop"' in metrics.render()


@patch("wanwatcher.ddns.duckdns.requests.get")
def test_retry_after_failure(mock_get):
    # First attempt fails, address is not cached, so it retries next time.
    mock_get.return_value = MagicMock(ok=True, status_code=200, text="KO")
    client = _duck(["home"])
    client.update("1.2.3.4", None)
    assert mock_get.call_count == 1
    mock_get.return_value = MagicMock(ok=True, status_code=200, text="OK")
    client.update("1.2.3.4", None)
    assert mock_get.call_count == 2


@patch("wanwatcher.ddns.duckdns.requests.get")
def test_update_never_raises(mock_get):
    import requests

    mock_get.side_effect = requests.RequestException("boom")
    client = _duck(["home"])
    # Must swallow the error and report failure rather than raising.
    assert client.update("1.2.3.4", None) == {"home": False}


# -- Cloudflare -------------------------------------------------------------


def _cf():
    return CloudflareClient(
        CloudflareConfig(
            api_token="tok",
            zone="example.com",
            records=["home.example.com"],
            proxied=False,
            ttl=1,
        )
    )


@patch("wanwatcher.ddns.cloudflare.requests.request")
def test_cloudflare_creates_missing_record(mock_req):
    def respond(method, url, **kwargs):
        if "/zones" in url and url.endswith("/zones"):
            return MagicMock(
                status_code=200,
                json=lambda: {"success": True, "result": [{"id": "zone1"}]},
            )
        if "/dns_records" in url and method == "GET":
            return MagicMock(
                status_code=200, json=lambda: {"success": True, "result": []}
            )
        if "/dns_records" in url and method == "POST":
            return MagicMock(
                status_code=200,
                json=lambda: {"success": True, "result": {"id": "rec1"}},
            )
        raise AssertionError(f"unexpected {method} {url}")

    mock_req.side_effect = respond
    client = _cf()
    result = client.update("1.2.3.4", None)
    assert result == {"home.example.com/A": True}


@patch("wanwatcher.ddns.cloudflare.requests.request")
def test_cloudflare_updates_existing_record(mock_req):
    def respond(method, url, **kwargs):
        if url.endswith("/zones"):
            return MagicMock(
                status_code=200,
                json=lambda: {"success": True, "result": [{"id": "zone1"}]},
            )
        if "/dns_records" in url and method == "GET":
            return MagicMock(
                status_code=200,
                json=lambda: {
                    "success": True,
                    "result": [{"id": "rec1", "content": "9.9.9.9", "proxied": False}],
                },
            )
        if method == "PUT":
            return MagicMock(
                status_code=200,
                json=lambda: {"success": True, "result": {"id": "rec1"}},
            )
        raise AssertionError(f"unexpected {method} {url}")

    mock_req.side_effect = respond
    client = _cf()
    assert client.update("1.2.3.4", None) == {"home.example.com/A": True}
    assert any(c.args[0] == "PUT" for c in mock_req.call_args_list)


@patch("wanwatcher.ddns.cloudflare.requests.request")
def test_cloudflare_zone_failure_marks_all_failed(mock_req):
    mock_req.return_value = MagicMock(
        status_code=403, json=lambda: {"success": False, "errors": ["nope"]}
    )
    client = _cf()
    result = client.update("1.2.3.4", None)
    assert result == {"home.example.com/A": False}
