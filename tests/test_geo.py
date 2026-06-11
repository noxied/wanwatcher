"""Tests for the ipinfo.io geo lookup."""

from unittest.mock import MagicMock, patch

from wanwatcher.geo import get_geo_data


def test_no_token_returns_none():
    assert get_geo_data("") is None


@patch("wanwatcher.geo.requests.get")
def test_successful_lookup(mock_get):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "city": "Lisbon",
        "region": "Lisbon",
        "country": "PT",
        "org": "AS1234 Example",
        "timezone": "Europe/Lisbon",
    }
    mock_get.return_value = resp
    data = get_geo_data("token")
    assert data["city"] == "Lisbon"
    assert data["country"] == "PT"
    # Token must be sent as a bearer header, not in the URL.
    assert "Bearer token" in mock_get.call_args.kwargs["headers"]["Authorization"]


@patch("wanwatcher.geo.requests.get")
def test_network_error_returns_none(mock_get):
    import requests

    mock_get.side_effect = requests.exceptions.Timeout("slow")
    assert get_geo_data("token") is None


@patch("wanwatcher.geo.requests.get")
def test_non_dict_payload_returns_none(mock_get):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = ["unexpected"]
    mock_get.return_value = resp
    assert get_geo_data("token") is None
