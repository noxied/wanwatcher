"""Public IP detection from multiple independent sources.

Sources are tried in rotating order so load is spread between services and a
single broken or rate-limited service never blocks detection. Every response
is parsed strictly through the ipaddress module; anything that is not a clean
global address is rejected.
"""

import ipaddress
import logging
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def _parse_json_ip(text_key: str) -> Callable[[requests.Response], Optional[str]]:
    def parser(response: requests.Response) -> Optional[str]:
        data = response.json()
        if not isinstance(data, dict):
            return None
        value = data.get(text_key)
        return value.strip() if isinstance(value, str) else None

    return parser


def _parse_plain(response: requests.Response) -> Optional[str]:
    return response.text.strip()


def _parse_cloudflare_trace(response: requests.Response) -> Optional[str]:
    for line in response.text.splitlines():
        if line.startswith("ip="):
            return line[3:].strip()
    return None


@dataclass
class Source:
    name: str
    url: str
    parser: Callable[[requests.Response], Optional[str]]


IPV4_SOURCES: List[Source] = [
    Source("ipify", "https://api.ipify.org?format=json", _parse_json_ip("ip")),
    Source("cloudflare", "https://1.1.1.1/cdn-cgi/trace", _parse_cloudflare_trace),
    Source("icanhazip", "https://ipv4.icanhazip.com", _parse_plain),
    Source("ifconfig.me", "https://ifconfig.me/ip", _parse_plain),
    Source("ident.me", "https://v4.ident.me", _parse_plain),
]

IPV6_SOURCES: List[Source] = [
    Source("ipify6", "https://api6.ipify.org?format=json", _parse_json_ip("ip")),
    Source("icanhazip6", "https://ipv6.icanhazip.com", _parse_plain),
    Source("ident.me6", "https://v6.ident.me", _parse_plain),
]


def is_valid_ipv4(ip_str: str) -> bool:
    """Accept only globally routable unicast IPv4 addresses."""
    try:
        ip_obj = ipaddress.IPv4Address(ip_str)
    except (ipaddress.AddressValueError, ValueError):
        return False
    return not (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )


def is_valid_ipv6(ip_str: str) -> bool:
    """Accept only globally routable IPv6 addresses.

    Link-local, loopback, multicast, private (ULA) and reserved ranges are
    rejected so interface noise never gets reported as a WAN address.
    """
    try:
        ip_obj = ipaddress.IPv6Address(ip_str)
    except (ipaddress.AddressValueError, ValueError):
        logger.debug("Invalid IPv6 format: %s", ip_str)
        return False

    if ip_obj.is_loopback:
        logger.debug("Rejected IPv6 (loopback): %s", ip_str)
        return False
    if ip_obj.is_link_local:
        logger.debug("Rejected IPv6 (link-local): %s", ip_str)
        return False
    if ip_obj.is_multicast:
        logger.debug("Rejected IPv6 (multicast): %s", ip_str)
        return False
    if ip_obj.is_private:
        logger.debug("Rejected IPv6 (private): %s", ip_str)
        return False
    if ip_obj.is_reserved:
        logger.debug("Rejected IPv6 (reserved): %s", ip_str)
        return False
    return True


class IPDetector:
    """Detects the current public IPv4/IPv6 with rotation and confirmation."""

    def __init__(self, timeout: int = 10, change_confirmation: bool = True):
        self.timeout = timeout
        self.change_confirmation = change_confirmation
        self._ipv4_offset = 0
        self._ipv6_offset = 0

    # -- internals ---------------------------------------------------------

    def _query(self, source: Source, validator: Callable[[str], bool]) -> Optional[str]:
        try:
            response = requests.get(source.url, timeout=self.timeout)
            response.raise_for_status()
            ip = source.parser(response)
        except requests.exceptions.RequestException as exc:
            logger.warning("IP source %s failed: %s", source.name, exc)
            return None
        except ValueError as exc:
            logger.warning(
                "IP source %s returned unparsable data: %s", source.name, exc
            )
            return None

        if ip and validator(ip):
            logger.debug("Source %s reports %s", source.name, ip)
            return ip
        logger.debug("Source %s returned invalid address: %r", source.name, ip)
        return None

    def _detect(
        self,
        sources: List[Source],
        offset: int,
        validator: Callable[[str], bool],
        previous: Optional[str],
    ) -> Tuple[Optional[str], int]:
        """Try sources in rotating order; confirm changes with a second source.

        Returns (ip, sources_consulted). ip is None when every source failed.
        """
        order = [sources[(offset + i) % len(sources)] for i in range(len(sources))]
        first_result: Optional[str] = None
        first_source_idx: Optional[int] = None

        for idx, source in enumerate(order):
            ip = self._query(source, validator)
            if ip is None:
                continue
            if first_result is None:
                first_result = ip
                first_source_idx = idx
                needs_confirmation = (
                    self.change_confirmation and previous is not None and ip != previous
                )
                if not needs_confirmation:
                    return ip, idx + 1
                logger.info(
                    "Source %s reports a different address than stored; "
                    "confirming with a second source",
                    source.name,
                )
                continue
            # Second opinion obtained
            if ip == first_result:
                return ip, idx + 1
            logger.warning(
                "IP sources disagree (%s vs %s); trusting the matching pair on "
                "the next round and keeping the stored address for now",
                first_result,
                ip,
            )
            return previous, idx + 1

        if first_result is not None:
            # A change was detected but no second source was reachable.
            # Report it anyway rather than going silent.
            logger.info(
                "Change confirmation unavailable (no second source reachable); "
                "accepting %s from a single source",
                first_result,
            )
            return first_result, (first_source_idx or 0) + 1
        return None, len(order)

    # -- public API --------------------------------------------------------

    def get_ipv4(self, previous: Optional[str] = None) -> Optional[str]:
        ip, consulted = self._detect(
            IPV4_SOURCES, self._ipv4_offset, is_valid_ipv4, previous
        )
        self._ipv4_offset = (self._ipv4_offset + 1) % len(IPV4_SOURCES)
        if ip is None:
            logger.warning("Failed to retrieve IPv4 from all %d sources", consulted)
        return ip

    def get_ipv6(self, previous: Optional[str] = None) -> Optional[str]:
        ip, consulted = self._detect(
            IPV6_SOURCES, self._ipv6_offset, is_valid_ipv6, previous
        )
        self._ipv6_offset = (self._ipv6_offset + 1) % len(IPV6_SOURCES)
        if ip is None:
            logger.warning("Failed to retrieve IPv6 from all %d sources", consulted)
        return ip
