#!/usr/bin/env python3
"""Container healthcheck for WANwatcher.

When the status API is enabled, asks it directly. Otherwise verifies that the
state file exists, contains valid JSON and was refreshed recently (the main
loop rewrites it after every successful check).
"""

import json
import os
import sys
import time


def check_api(port: int) -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/healthz", timeout=5
        ) as response:
            return response.status == 200
    except Exception:
        return False


def check_state_file(path: str, interval: int) -> bool:
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            json.load(fh)
    except (OSError, json.JSONDecodeError):
        return False
    max_age = max(3 * interval, 1800) + 120
    return (time.time() - os.path.getmtime(path)) <= max_age


def main() -> int:
    api_enabled = os.environ.get("API_ENABLED", "false").lower() == "true"
    if api_enabled:
        port = int(os.environ.get("API_PORT", "8080") or "8080")
        return 0 if check_api(port) else 1

    state_file = os.environ.get("IP_DB_FILE", "/data/ipinfo.db")
    try:
        interval = int(os.environ.get("CHECK_INTERVAL", "900") or "900")
    except ValueError:
        interval = 900
    return 0 if check_state_file(state_file, interval) else 1


if __name__ == "__main__":
    sys.exit(main())
