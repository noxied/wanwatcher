"""AWS Route53 updater using the REST API signed with Signature V4.

Route53 has no lightweight client, and boto3 would add tens of megabytes to the
image, so the AWS SigV4 signing is implemented here with the standard library
(hashlib/hmac) plus requests. All configured records are sent in a single
atomic ChangeResourceRecordSets batch (UPSERT).
"""

import datetime as _dt
import hashlib
import hmac
import logging
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

import requests

from wanwatcher.config import Route53Config, redact
from wanwatcher.ddns.base import DDNSClient
from wanwatcher.metrics import Metrics

logger = logging.getLogger(__name__)

HOST = "route53.amazonaws.com"
API_VERSION = "2013-04-01"
REGION = "us-east-1"  # Route53 is global but always signs against us-east-1
SERVICE = "route53"
XMLNS = "https://route53.amazonaws.com/doc/2013-04-01/"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, datestamp: str) -> bytes:
    k_date = _hmac(("AWS4" + secret).encode("utf-8"), datestamp)
    k_region = _hmac(k_date, REGION)
    k_service = _hmac(k_region, SERVICE)
    return _hmac(k_service, "aws4_request")


def sigv4_headers(
    access_key: str,
    secret_key: str,
    canonical_uri: str,
    body: bytes,
    now: _dt.datetime,
) -> Dict[str, str]:
    """Build the SigV4 Authorization headers for a Route53 POST request."""
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")
    payload_hash = _sha256_hex(body)

    canonical_headers = (
        f"host:{HOST}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        ["POST", canonical_uri, "", canonical_headers, signed_headers, payload_hash]
    )

    credential_scope = f"{datestamp}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            _sha256_hex(canonical_request.encode("utf-8")),
        ]
    )
    signature = hmac.new(
        _signing_key(secret_key, datestamp),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    authorization = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return {
        "Authorization": authorization,
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Content-Type": "application/xml",
    }


class Route53Client(DDNSClient):
    provider = "route53"

    def __init__(
        self,
        config: Route53Config,
        timeout: int = 10,
        metrics: Optional[Metrics] = None,
    ) -> None:
        super().__init__(timeout=timeout, metrics=metrics)
        self.config = config
        # Accept both "Z123" and "/hostedzone/Z123".
        self.zone_id = config.hosted_zone_id.rsplit("/", 1)[-1]

    def _build_change_batch(self, ipv4: Optional[str], ipv6: Optional[str]) -> str:
        changes: List[str] = []
        for fqdn in self.config.records:
            name = escape(fqdn)
            for record_type, value in (("A", ipv4), ("AAAA", ipv6)):
                if not value:
                    continue
                changes.append(
                    "<Change><Action>UPSERT</Action><ResourceRecordSet>"
                    f"<Name>{name}</Name><Type>{record_type}</Type>"
                    f"<TTL>{self.config.ttl}</TTL>"
                    "<ResourceRecords><ResourceRecord>"
                    f"<Value>{escape(value)}</Value>"
                    "</ResourceRecord></ResourceRecords>"
                    "</ResourceRecordSet></Change>"
                )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<ChangeResourceRecordSetsRequest xmlns="{XMLNS}"><ChangeBatch>'
            "<Comment>WANwatcher update</Comment>"
            f"<Changes>{''.join(changes)}</Changes>"
            "</ChangeBatch></ChangeResourceRecordSetsRequest>"
        )

    def _targets(
        self, ipv4: Optional[str], ipv6: Optional[str]
    ) -> List[Tuple[str, str, str]]:
        targets: List[Tuple[str, str, str]] = []
        if ipv4:
            targets.append(("A", ipv4, "ipv4"))
        if ipv6:
            targets.append(("AAAA", ipv6, "ipv6"))
        return targets

    def _apply(self, ipv4: Optional[str], ipv6: Optional[str]) -> Dict[str, bool]:
        targets = self._targets(ipv4, ipv6)
        results: Dict[str, bool] = {
            f"{fqdn}/{rtype}": False
            for fqdn in self.config.records
            for rtype, _value, _family in targets
        }
        if not results:
            return results

        body = self._build_change_batch(ipv4, ipv6).encode("utf-8")
        canonical_uri = f"/{API_VERSION}/hostedzone/{self.zone_id}/rrset"
        now = _dt.datetime.now(_dt.timezone.utc)
        headers = sigv4_headers(
            self.config.access_key_id,
            self.config.secret_access_key,
            canonical_uri,
            body,
            now,
        )

        ok = False
        try:
            response = requests.post(
                f"https://{HOST}{canonical_uri}",
                data=body,
                headers=headers,
                timeout=self.timeout,
            )
            ok = response.status_code == 200
            if not ok:
                logger.error(
                    "Route53: update rejected (HTTP %d, key %s): %s",
                    response.status_code,
                    redact(self.config.access_key_id),
                    response.text[:300],
                )
        except requests.RequestException as exc:
            logger.error("Route53: update request failed: %s", type(exc).__name__)

        if ok:
            logger.info("Route53: updated %s", ", ".join(self.config.records))
            return {key: True for key in results}

        for _rtype, _value, family in targets:
            self._mark_failure(family)
        return results
