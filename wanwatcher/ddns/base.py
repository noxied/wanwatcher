"""Shared behavior for DDNS clients.

The base class handles change caching (so unchanged addresses are a cheap
no-op), per-family retry on failure, metrics, and error containment: an
exception inside a provider must never escape into the monitoring loop.
"""

import logging
from typing import Dict, Optional

from wanwatcher.metrics import Metrics

logger = logging.getLogger(__name__)

FAMILIES = ("ipv4", "ipv6")


class DDNSClient:
    """Base class for DDNS providers.

    Subclasses implement ``_apply(ipv4, ipv6)`` which performs the actual
    record updates and returns per-record (or per-hostname) success flags.
    Subclasses must call ``_mark_failure(family)`` for every address family
    affected by a failed update so the base class retries it next check.
    """

    provider: str = "ddns"

    def __init__(self, timeout: int = 10, metrics: Optional[Metrics] = None) -> None:
        self.timeout = timeout
        self.metrics = metrics
        # family ("ipv4" / "ipv6") -> last successfully applied address
        self._applied: Dict[str, str] = {}
        # Reset before every _apply call; subclasses flag failures into it.
        self._family_ok: Dict[str, bool] = {family: True for family in FAMILIES}

    # -- subclass interface ---------------------------------------------------

    def _apply(self, ipv4: Optional[str], ipv6: Optional[str]) -> Dict[str, bool]:
        """Push the given addresses to the provider.

        Returns a mapping of record/hostname identifier to success flag.
        """
        raise NotImplementedError

    def _mark_failure(self, family: str) -> None:
        """Record that an update for the given address family failed."""
        self._family_ok[family] = False

    # -- helpers ----------------------------------------------------------------

    def _inc(self, result: str) -> None:
        if self.metrics is not None:
            self.metrics.inc(
                "wanwatcher_ddns_updates_total",
                {"provider": self.provider, "result": result},
            )

    # -- public API ---------------------------------------------------------------

    def update(self, ipv4: Optional[str], ipv6: Optional[str]) -> Dict[str, bool]:
        """Update DNS records for the given addresses.

        A cheap no-op when both addresses match the last successful update.
        Never raises; failures are logged and retried on the next check.
        """
        wanted = {"ipv4": ipv4, "ipv6": ipv6}
        pending = {
            family: address
            for family, address in wanted.items()
            if address is not None and self._applied.get(family) != address
        }
        if not pending:
            logger.debug(
                "DDNS (%s): no address changes since last successful update, "
                "skipping",
                self.provider,
            )
            self._inc("noop")
            return {}

        logger.info(
            "DDNS (%s): applying %s",
            self.provider,
            ", ".join(f"{family}={address}" for family, address in pending.items()),
        )

        self._family_ok = {family: True for family in FAMILIES}
        try:
            results = self._apply(ipv4, ipv6)
        except Exception as exc:  # noqa: BLE001 - must never break the main loop
            logger.error("DDNS (%s): update failed: %s", self.provider, exc)
            self._inc("error")
            return {}

        if results:
            # Only cache families that fully succeeded so the rest retry.
            for family in FAMILIES:
                address = wanted[family]
                if address is not None and self._family_ok[family]:
                    self._applied[family] = address

        if results and all(results.values()):
            logger.info(
                "DDNS (%s): all %d record(s) up to date", self.provider, len(results)
            )
            self._inc("ok")
        else:
            failed = sorted(name for name, ok in results.items() if not ok)
            logger.error(
                "DDNS (%s): update incomplete, failed: %s",
                self.provider,
                ", ".join(failed) if failed else "(no records processed)",
            )
            self._inc("error")
        return results
