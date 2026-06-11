"""Generic dyndns2 protocol client (No-IP, Dynu, DynDNS and compatibles).

Each hostname is updated with GET {server}/nic/update?hostname=...&myip=...
over HTTPS with Basic auth. Response bodies starting with "good" or
"nochg" mean success; "badauth", "nohost", "abuse", "911" etc. are
failures.
"""

import logging
from typing import Dict, Optional

import requests

from wanwatcher.config import DynDNS2Config
from wanwatcher.ddns.base import DDNSClient
from wanwatcher.metrics import Metrics

logger = logging.getLogger(__name__)

USER_AGENT = "WANwatcher/2.0 github.com/noxied/wanwatcher"
SUCCESS_CODES = ("good", "nochg")


class DynDNS2Client(DDNSClient):
    provider = "dyndns2"

    def __init__(
        self,
        config: DynDNS2Config,
        timeout: int = 10,
        metrics: Optional[Metrics] = None,
    ) -> None:
        super().__init__(timeout=timeout, metrics=metrics)
        self.config = config
        self.server = self._normalize_server(config.server)

    @staticmethod
    def _normalize_server(server: str) -> str:
        """Force an https:// scheme; credentials must not travel in clear."""
        server = server.strip().rstrip("/")
        if server.startswith("http://"):
            server = "https://" + server[len("http://") :]
        elif server and not server.startswith("https://"):
            server = "https://" + server
        return server

    def _update_hostname(self, hostname: str, myip: str) -> bool:
        try:
            response = requests.get(
                f"{self.server}/nic/update",
                params={"hostname": hostname, "myip": myip},
                auth=(self.config.username, self.config.password),
                headers={"User-Agent": USER_AGENT},
                timeout=self.timeout,
            )
            body = response.text.strip()
        except requests.RequestException as exc:
            logger.error("dyndns2: update of %s failed: %s", hostname, exc)
            return False

        code = body.split()[0].lower() if body else ""
        if code in SUCCESS_CODES:
            logger.info("dyndns2: %s -> %s (%s)", hostname, myip, code)
            return True
        logger.error(
            "dyndns2: update of %s rejected with %r (HTTP %d)",
            hostname,
            code or "(empty body)",
            response.status_code,
        )
        return False

    def _apply(self, ipv4: Optional[str], ipv6: Optional[str]) -> Dict[str, bool]:
        if ipv4 and ipv6:
            # dyndns2 convention: comma-separated dual-stack update.
            myip = f"{ipv4},{ipv6}"
        else:
            myip = ipv4 or ipv6 or ""

        results: Dict[str, bool] = {}
        for hostname in self.config.hostnames:
            ok = self._update_hostname(hostname, myip)
            results[hostname] = ok
            if not ok:
                # One request carries both families, so a failed hostname
                # means neither family is confirmed applied.
                self._mark_failure("ipv4")
                self._mark_failure("ipv6")
        return results
