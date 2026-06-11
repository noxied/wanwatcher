"""Update checking against GitHub releases."""

import logging
from typing import Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/repos/noxied/wanwatcher/releases/latest"


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse 'v1.2.3' or '1.2.3' into a comparable tuple. Unparsable -> (0,0,0)."""
    try:
        parts = version_str.lstrip("v").split(".")
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError, AttributeError):
        logger.debug("Could not parse version string: %r", version_str)
        return (0, 0, 0)


def check_for_updates(
    current_version: str,
    already_notified: Optional[str] = None,
    timeout: int = 10,
) -> Optional[Dict[str, str]]:
    """Return release info when a newer version exists and was not yet notified."""
    try:
        logger.info("Checking for updates...")
        response = requests.get(GITHUB_API_URL, timeout=timeout)
        response.raise_for_status()
        release_data = response.json()
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("Update check failed: %s", exc)
        return None

    if not isinstance(release_data, dict):
        logger.warning("Update check returned unexpected payload")
        return None

    latest_version = release_data.get("tag_name", "").lstrip("v")
    current = current_version.lstrip("v")

    if parse_version(latest_version) <= parse_version(current):
        logger.info("WANwatcher is up to date")
        return None

    if already_notified == latest_version:
        logger.info("Already notified about v%s", latest_version)
        return None

    logger.info("New version available: v%s (current: v%s)", latest_version, current)
    return {
        "current_version": current,
        "latest_version": latest_version,
        "release_name": release_data.get("name", ""),
        "release_url": release_data.get("html_url", ""),
        "release_body": release_data.get("body", ""),
        "published_at": release_data.get("published_at", ""),
    }
