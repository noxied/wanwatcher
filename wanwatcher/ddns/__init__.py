"""DDNS update clients for WANwatcher.

Use :func:`build_ddns_client` to construct the client matching the
configured provider; it returns ``None`` (with an error log) when the
provider is unknown or its configuration is incomplete.
"""

import logging
from typing import Optional

from wanwatcher.config import DDNSConfig
from wanwatcher.ddns.base import DDNSClient
from wanwatcher.ddns.cloudflare import CloudflareClient
from wanwatcher.ddns.duckdns import DuckDNSClient
from wanwatcher.ddns.dyndns2 import DynDNS2Client
from wanwatcher.metrics import Metrics

logger = logging.getLogger(__name__)

__all__ = [
    "CloudflareClient",
    "DDNSClient",
    "DuckDNSClient",
    "DynDNS2Client",
    "build_ddns_client",
]


def build_ddns_client(
    config: DDNSConfig, timeout: int = 10, metrics: Optional[Metrics] = None
) -> Optional[DDNSClient]:
    """Build the DDNS client for the configured provider, or None."""
    provider = (config.provider or "").strip().lower()

    if provider == "cloudflare":
        cloudflare = config.cloudflare
        if not (cloudflare.api_token and cloudflare.zone and cloudflare.records):
            logger.error(
                "DDNS: cloudflare provider needs CLOUDFLARE_API_TOKEN, "
                "CLOUDFLARE_ZONE and CLOUDFLARE_RECORDS - DDNS disabled"
            )
            return None
        return CloudflareClient(cloudflare, timeout=timeout, metrics=metrics)

    if provider == "duckdns":
        duckdns = config.duckdns
        if not (duckdns.token and duckdns.domains):
            logger.error(
                "DDNS: duckdns provider needs DUCKDNS_TOKEN and "
                "DUCKDNS_DOMAINS - DDNS disabled"
            )
            return None
        return DuckDNSClient(duckdns, timeout=timeout, metrics=metrics)

    if provider == "dyndns2":
        dyndns2 = config.dyndns2
        if not (
            dyndns2.server
            and dyndns2.username
            and dyndns2.password
            and dyndns2.hostnames
        ):
            logger.error(
                "DDNS: dyndns2 provider needs DYNDNS2_SERVER, DYNDNS2_USERNAME, "
                "DYNDNS2_PASSWORD and DYNDNS2_HOSTNAMES - DDNS disabled"
            )
            return None
        return DynDNS2Client(dyndns2, timeout=timeout, metrics=metrics)

    logger.error(
        "DDNS: unknown provider %r (expected cloudflare, duckdns or dyndns2) "
        "- DDNS disabled",
        config.provider,
    )
    return None
