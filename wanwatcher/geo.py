"""Geographic information lookup via ipinfo.io. Optional, degrades silently."""

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

IPINFO_URL = "https://ipinfo.io/json"


def get_geo_data(token: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """Fetch geo data for the current public IP. Returns None on any failure."""
    if not token:
        return None

    try:
        response = requests.get(
            IPINFO_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("ipinfo.io lookup failed: %s", exc)
        return None

    if not isinstance(data, dict):
        logger.warning("ipinfo.io returned unexpected payload")
        return None

    return {
        "city": data.get("city"),
        "region": data.get("region"),
        "country": data.get("country"),
        "org": data.get("org"),
        "timezone": data.get("timezone"),
    }
