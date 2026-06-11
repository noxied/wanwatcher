"""Cloudflare DNS updater using the v4 API with a scoped bearer token.

Resolves the zone id once, then upserts an A record (IPv4) and/or AAAA
record (IPv6) for every configured FQDN. Each record is handled
independently so one bad record does not block the others.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

from wanwatcher.config import CloudflareConfig
from wanwatcher.ddns.base import DDNSClient
from wanwatcher.metrics import Metrics

logger = logging.getLogger(__name__)

API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareClient(DDNSClient):
    provider = "cloudflare"

    def __init__(
        self,
        config: CloudflareConfig,
        timeout: int = 10,
        metrics: Optional[Metrics] = None,
    ) -> None:
        super().__init__(timeout=timeout, metrics=metrics)
        self.config = config
        self._zone_id: Optional[str] = None

    # -- HTTP helpers ----------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
        """Perform an API call; returns (status_code, payload) or (None, None)."""
        try:
            response = requests.request(
                method,
                f"{API_BASE}{path}",
                headers=self._headers(),
                params=params,
                json=json_body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            logger.error("Cloudflare: %s %s failed: %s", method, path, exc)
            return None, None
        try:
            payload = response.json()
        except ValueError:
            logger.error(
                "Cloudflare: %s %s returned non-JSON body (HTTP %d)",
                method,
                path,
                response.status_code,
            )
            return response.status_code, None
        return response.status_code, payload

    # -- zone resolution ----------------------------------------------------------

    def _resolve_zone_id(self) -> Optional[str]:
        if self._zone_id:
            return self._zone_id
        status, payload = self._request(
            "GET", "/zones", params={"name": self.config.zone}
        )
        if payload is None or not payload.get("success"):
            logger.error(
                "Cloudflare: zone lookup for %r failed (HTTP %s): %s",
                self.config.zone,
                status,
                (payload or {}).get("errors"),
            )
            return None
        zones: List[Dict[str, Any]] = payload.get("result") or []
        if not zones:
            logger.error(
                "Cloudflare: zone %r not found (check the token's zone access)",
                self.config.zone,
            )
            return None
        self._zone_id = str(zones[0]["id"])
        logger.info(
            "Cloudflare: resolved zone %s to id %s", self.config.zone, self._zone_id
        )
        return self._zone_id

    # -- record updates --------------------------------------------------------------

    def _upsert_record(
        self, zone_id: str, fqdn: str, record_type: str, content: str
    ) -> bool:
        """Create or update one DNS record; returns True on success."""
        status, payload = self._request(
            "GET",
            f"/zones/{zone_id}/dns_records",
            params={"type": record_type, "name": fqdn},
        )
        if payload is None or not payload.get("success"):
            logger.error(
                "Cloudflare: lookup of %s record %s failed (HTTP %s): %s",
                record_type,
                fqdn,
                status,
                (payload or {}).get("errors"),
            )
            return False

        body: Dict[str, Any] = {
            "type": record_type,
            "name": fqdn,
            "content": content,
            "proxied": self.config.proxied,
            "ttl": self.config.ttl,  # 1 means "automatic"
        }
        records: List[Dict[str, Any]] = payload.get("result") or []
        if records:
            record = records[0]
            if (
                record.get("content") == content
                and record.get("proxied") == self.config.proxied
            ):
                logger.debug(
                    "Cloudflare: %s record %s already set to %s",
                    record_type,
                    fqdn,
                    content,
                )
                return True
            action = "update"
            status, payload = self._request(
                "PUT",
                f"/zones/{zone_id}/dns_records/{record['id']}",
                json_body=body,
            )
        else:
            action = "create"
            status, payload = self._request(
                "POST", f"/zones/{zone_id}/dns_records", json_body=body
            )

        if payload is not None and payload.get("success"):
            logger.info(
                "Cloudflare: %sd %s record %s -> %s",
                action,
                record_type,
                fqdn,
                content,
            )
            return True
        logger.error(
            "Cloudflare: failed to %s %s record %s (HTTP %s): %s",
            action,
            record_type,
            fqdn,
            status,
            (payload or {}).get("errors"),
        )
        return False

    def _apply(self, ipv4: Optional[str], ipv6: Optional[str]) -> Dict[str, bool]:
        targets: List[Tuple[str, str, str]] = []
        if ipv4:
            targets.append(("A", ipv4, "ipv4"))
        if ipv6:
            targets.append(("AAAA", ipv6, "ipv6"))

        results: Dict[str, bool] = {}
        zone_id = self._resolve_zone_id()
        if zone_id is None:
            for fqdn in self.config.records:
                for record_type, _address, family in targets:
                    results[f"{fqdn}/{record_type}"] = False
                    self._mark_failure(family)
            return results

        for fqdn in self.config.records:
            for record_type, address, family in targets:
                ok = self._upsert_record(zone_id, fqdn, record_type, address)
                results[f"{fqdn}/{record_type}"] = ok
                if not ok:
                    self._mark_failure(family)
        return results
