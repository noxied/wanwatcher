"""Tests for GitHub update checking."""

from unittest.mock import MagicMock, patch

from wanwatcher.updates import check_for_updates, parse_version


def test_parse_version_normal():
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("v2.0.0") == (2, 0, 0)


def test_parse_version_garbage():
    assert parse_version("not-a-version") == (0, 0, 0)
    assert parse_version("") == (0, 0, 0)
    assert parse_version("1.2") == (0, 0, 0)


def test_parse_version_ordering():
    assert parse_version("2.0.0") > parse_version("1.9.9")
    assert parse_version("1.4.1") > parse_version("1.4.0")


def _release(tag):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "tag_name": tag,
        "name": f"Release {tag}",
        "html_url": f"https://github.com/noxied/wanwatcher/releases/{tag}",
        "body": "notes",
        "published_at": "2026-01-01T00:00:00Z",
    }
    return resp


@patch("wanwatcher.updates.requests.get")
def test_newer_version_returns_info(mock_get):
    mock_get.return_value = _release("v2.1.0")
    info = check_for_updates("2.0.0")
    assert info is not None
    assert info["latest_version"] == "2.1.0"
    assert info["current_version"] == "2.0.0"


@patch("wanwatcher.updates.requests.get")
def test_same_version_returns_none(mock_get):
    mock_get.return_value = _release("v2.0.0")
    assert check_for_updates("2.0.0") is None


@patch("wanwatcher.updates.requests.get")
def test_already_notified_returns_none(mock_get):
    mock_get.return_value = _release("v2.1.0")
    assert check_for_updates("2.0.0", already_notified="2.1.0") is None


@patch("wanwatcher.updates.requests.get")
def test_network_error_returns_none(mock_get):
    import requests

    mock_get.side_effect = requests.exceptions.ConnectionError("down")
    assert check_for_updates("2.0.0") is None
