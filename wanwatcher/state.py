"""State persistence with atomic writes and migration from older formats."""

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 20


@dataclass
class State:
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    last_updated: Optional[str] = None
    last_change: Optional[str] = None
    update_notified_version: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    def is_empty(self) -> bool:
        return self.ipv4 is None and self.ipv6 is None


class StateStore:
    """Reads and writes the JSON state file.

    Writes go to a temporary file in the same directory followed by
    os.replace(), so a crash mid-write can never corrupt the state.
    Old formats (plain-text IPv4, bare JSON string, v1 dict) are migrated
    transparently on first read.
    """

    def __init__(self, path: str, legacy_update_file: Optional[str] = None):
        self.path = path
        self.legacy_update_file = legacy_update_file

    def load(self) -> State:
        if not os.path.exists(self.path):
            logger.info("No previous state found (first run)")
            return self._with_legacy_update_version(State())

        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                content = fh.read().strip()
        except OSError as exc:
            logger.error("Could not read state file %s: %s", self.path, exc)
            return State()

        if not content:
            return State()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # v0 format: plain text file containing just the IPv4 address
            logger.info("Migrating plain-text state file to JSON format")
            return self._with_legacy_update_version(State(ipv4=content))

        if isinstance(data, str):
            # An old bug stored the IP as a bare JSON string
            logger.info("Migrating legacy string state to JSON format")
            return self._with_legacy_update_version(State(ipv4=data))

        if not isinstance(data, dict):
            logger.error("State file has unexpected structure, starting fresh")
            return State()

        state = State(
            ipv4=data.get("ipv4"),
            ipv6=data.get("ipv6"),
            last_updated=data.get("last_updated"),
            last_change=data.get("last_change"),
            update_notified_version=data.get("update_notified_version"),
            history=data.get("history") or [],
        )
        if state.update_notified_version is None:
            state = self._with_legacy_update_version(state)
        return state

    def save(self, state: State) -> None:
        state.last_updated = datetime.now(timezone.utc).isoformat()
        directory = os.path.dirname(self.path) or "."
        os.makedirs(directory, exist_ok=True)

        payload = json.dumps(asdict(state), indent=2)
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".state-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp_path, self.path)
        except OSError:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        logger.debug("State saved: ipv4=%s ipv6=%s", state.ipv4, state.ipv6)

    def record_change(
        self,
        state: State,
        old_ipv4: Optional[str],
        old_ipv6: Optional[str],
    ) -> None:
        """Append a change entry to the bounded history and stamp last_change."""
        now = datetime.now(timezone.utc).isoformat()
        state.last_change = now
        state.history.append(
            {
                "at": now,
                "old_ipv4": old_ipv4,
                "new_ipv4": state.ipv4,
                "old_ipv6": old_ipv6,
                "new_ipv6": state.ipv6,
            }
        )
        if len(state.history) > HISTORY_LIMIT:
            state.history = state.history[-HISTORY_LIMIT:]

    def _with_legacy_update_version(self, state: State) -> State:
        """Absorb the old update_notified.txt sidecar file if present."""
        if not self.legacy_update_file:
            return state
        try:
            if os.path.exists(self.legacy_update_file):
                with open(self.legacy_update_file, "r", encoding="utf-8") as fh:
                    version = fh.read().strip()
                if version:
                    state.update_notified_version = version
                os.unlink(self.legacy_update_file)
                logger.info("Migrated update notification marker into state file")
        except OSError as exc:
            logger.warning("Could not migrate %s: %s", self.legacy_update_file, exc)
        return state
