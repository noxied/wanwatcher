"""DuckDNS updater.

A single GET to https://www.duckdns.org/update refreshes every configured
subdomain at once. The body is "OK" on success and "KO" on failure.
"""

import logging
from typing import Dict, Optional

import requests

from wanwatcher.config import DuckDNSConfig, redact
from wanwatcher.ddns.base import DDNSClient
from wanwatcher.metrics import Metrics

logger = logging.getLogger(__name__)

UPDATE_URL = "https://www.duckdns.org/update"
DUCKDNS_SUFFIX = ".duckdns.org"


class DuckDNSClient(DDNSClient):
    provider = "duckdns"

    def __init__(
        self,
        config: DuckDNSConfig,
        timeout: int = 10,
        metrics: Optional[Metrics] = None,
    ) -> None:
        super().__init__(timeout=timeout, metrics=metrics)
        self.config = config
        self.domains = [self._normalize(domain) for domain in config.domains]

    @staticmethod
    def _normalize(domain: str) -> str:
        """DuckDNS expects bare subdomain names without .duckdns.org."""
        domain = domain.strip().lower()
        if domain.endswith(DUCKDNS_SUFFIX):
            domain = domain[: -len(DUCKDNS_SUFFIX)]
        return domain.strip(".")

    def _apply(self, ipv4: Optional[str], ipv6: Optional[str]) -> Dict[str, bool]:
        params: Dict[str, str] = {
            "domains": ",".join(self.domains),
            "token": self.config.token,
        }
        if ipv4:
            params["ip"] = ipv4
        if ipv6:
            params["ipv6"] = ipv6

        ok = False
        try:
            response = requests.get(UPDATE_URL, params=params, timeout=self.timeout)
            body = response.text.strip()
            ok = response.ok and body.startswith("OK")
            if not ok:
                logger.error(
                    "DuckDNS: update rejected (HTTP %d, body %r, token %s)",
                    response.status_code,
                    body[:20],
                    redact(self.config.token),
                )
        except requests.RequestException as exc:
            # The exception text may contain the request URL (with the
            # token in the query string), so only log the exception type.
            logger.error("DuckDNS: update request failed: %s", type(exc).__name__)

        if ok:
            logger.info("DuckDNS: updated %s", ", ".join(self.domains))
        else:
            self._mark_failure("ipv4")
            self._mark_failure("ipv6")
        return {domain: ok for domain in self.domains}
