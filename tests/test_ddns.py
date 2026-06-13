"""Tests for the DDNS provider clients."""

from unittest.mock import MagicMock, patch

from wanwatcher.config import (
    CloudflareConfig,
    DDNSConfig,
    DuckDNSConfig,
    DynDNS2Config,
    Route53Config,
)
from wanwatcher.ddns import build_ddns_client
from wanwatcher.ddns.cloudflare import CloudflareClient
from wanwatcher.ddns.duckdns import DuckDNSClient
from wanwatcher.ddns.dyndns2 import DynDNS2Client
from wanwatcher.ddns.route53 import Route53Client, sigv4_headers
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


# -- Route53 ----------------------------------------------------------------


def _r53(records=None):
    return Route53Client(
        Route53Config(
            access_key_id="AKIAEXAMPLE",
            secret_access_key="secret",
            hosted_zone_id="Z123ABC",
            records=records or ["home.example.com"],
            ttl=300,
        )
    )


def test_build_route53_ok():
    cfg = DDNSConfig(
        enabled=True,
        provider="route53",
        route53=Route53Config(
            access_key_id="AKIA",
            secret_access_key="s",
            hosted_zone_id="Z1",
            records=["home.example.com"],
        ),
    )
    assert isinstance(build_ddns_client(cfg), Route53Client)


def test_build_route53_missing_fields_returns_none():
    cfg = DDNSConfig(
        enabled=True,
        provider="route53",
        route53=Route53Config(access_key_id="AKIA"),  # missing the rest
    )
    assert build_ddns_client(cfg) is None


def test_route53_zone_id_strips_prefix():
    client = Route53Client(
        Route53Config(
            access_key_id="A",
            secret_access_key="s",
            hosted_zone_id="/hostedzone/Z999",
            records=["a.example.com"],
        )
    )
    assert client.zone_id == "Z999"


def test_sigv4_headers_deterministic():
    now = __import__("datetime").datetime(
        2026, 6, 13, 12, 0, 0, tzinfo=__import__("datetime").timezone.utc
    )
    h1 = sigv4_headers(
        "AKIA", "secret", "/2013-04-01/hostedzone/Z1/rrset", b"<x/>", now
    )
    h2 = sigv4_headers(
        "AKIA", "secret", "/2013-04-01/hostedzone/Z1/rrset", b"<x/>", now
    )
    assert h1 == h2
    assert h1["Authorization"].startswith("AWS4-HMAC-SHA256 Credential=AKIA/20260613/")
    assert "SignedHeaders=host;x-amz-content-sha256;x-amz-date" in h1["Authorization"]
    assert h1["x-amz-date"] == "20260613T120000Z"


@patch("wanwatcher.ddns.route53.requests.post")
def test_route53_upsert_success(mock_post):
    mock_post.return_value = MagicMock(status_code=200, text="<ChangeInfo/>")
    client = _r53(["home.example.com"])
    result = client.update("1.2.3.4", "2001:db8::1")
    assert result == {"home.example.com/A": True, "home.example.com/AAAA": True}
    body = mock_post.call_args.kwargs["data"].decode("utf-8")
    assert "<Action>UPSERT</Action>" in body
    assert "<Type>A</Type>" in body and "<Type>AAAA</Type>" in body
    assert "1.2.3.4" in body and "2001:db8::1" in body
    # signed request
    assert "Authorization" in mock_post.call_args.kwargs["headers"]


@patch("wanwatcher.ddns.route53.requests.post")
def test_route53_failure_marks_families(mock_post):
    mock_post.return_value = MagicMock(status_code=403, text="<Error>denied</Error>")
    client = _r53(["home.example.com"])
    assert client.update("1.2.3.4", None) == {"home.example.com/A": False}


@patch("wanwatcher.ddns.route53.requests.post")
def test_route53_network_error_never_raises(mock_post):
    import requests as _r

    mock_post.side_effect = _r.RequestException("boom")
    client = _r53(["home.example.com"])
    assert client.update("1.2.3.4", None) == {"home.example.com/A": False}


@patch("wanwatcher.ddns.route53.requests.post")
def test_route53_only_one_request_for_batch(mock_post):
    mock_post.return_value = MagicMock(status_code=200, text="<ChangeInfo/>")
    client = _r53(["a.example.com", "b.example.com"])
    client.update("1.2.3.4", None)
    # all records in a single atomic ChangeBatch
    assert mock_post.call_count == 1
