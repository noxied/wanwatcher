"""Base class and retry helper shared by all notification providers."""

import logging
import random
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


def retry_with_backoff(
    func: Callable[[], bool],
    max_retries: int = 3,
    base_delay: float = 1.0,
    jitter: float = 0.0,
) -> bool:
    """Retry a callable with exponential backoff and optional jitter.

    The callable signals failure either by returning False or by raising.
    Returns True as soon as one attempt succeeds. When ``jitter`` is greater
    than zero, a random amount in ``[0, jitter)`` seconds is added to each
    delay so concurrent retries do not all fire on the same instant.
    """

    def delay_for(attempt: int) -> float:
        delay = base_delay * (2**attempt)
        if jitter:
            delay += random.uniform(0, jitter)
        return delay

    for attempt in range(max_retries):
        try:
            if func():
                return True
            if attempt < max_retries - 1:
                delay = delay_for(attempt)
                logger.warning(
                    "Attempt %d failed, retrying in %.1fs...", attempt + 1, delay
                )
                time.sleep(delay)
        except (
            Exception
        ) as exc:  # noqa: BLE001 - provider errors must not crash the loop
            if attempt < max_retries - 1:
                delay = delay_for(attempt)
                logger.warning(
                    "Attempt %d failed with error: %s, retrying in %.1fs...",
                    attempt + 1,
                    exc,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error("All %d attempts failed: %s", max_retries, exc)
                return False
    return False


class NotificationProvider:
    """Base class for notification providers.

    v1 providers implemented send_notification() and
    send_update_notification(). v2 adds send_event() for generic messages
    (startup, heartbeat, outage, recovery); the base implementation logs and
    reports success so providers without a natural representation still work.
    """

    name = "base"

    def send_notification(
        self,
        current_ips: Dict[str, Optional[str]],
        previous_ips: Dict[str, Optional[str]],
        geo_data: Optional[Dict[str, Any]],
        is_first_run: bool,
        server_name: str,
        version: str = "",
    ) -> bool:
        raise NotImplementedError

    def send_update_notification(
        self, update_info: Dict[str, str], server_name: str, version: str = ""
    ) -> bool:
        raise NotImplementedError

    def send_event(
        self,
        title: str,
        message: str,
        server_name: str,
        severity: str = "info",
    ) -> bool:
        """Send a generic event message. severity: info | warning | error."""
        logger.info("[%s] %s: %s", self.name, title, message)
        return True
