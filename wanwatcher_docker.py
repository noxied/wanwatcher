#!/usr/bin/env python3
"""
WANwatcher Docker - WAN IP Address Monitor with Multi-Platform Notifications
Docker-optimized version with continuous loop mode

Version: 1.4.1

Features:
- Automatic IP change detection
- Multi-platform notifications (Discord, Telegram, Email)
- Custom Discord webhook avatars
- Detailed logging
- Error handling and recovery
- Supports multiple IP detection services as fallback
- Optional ipinfo.io integration for geographic data
- Continuous monitoring mode for Docker
- IPv6 support
"""

import ipaddress
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import requests

from config_validator import validate_config
from notifications import (
    DiscordNotifier,
    EmailNotifier,
    NotificationManager,
    TelegramNotifier,
)

# Version
VERSION = "1.4.1"

# ============================================================================
# CONFIGURATION - Loaded from Environment Variables
# ============================================================================

# Discord Configuration
DISCORD_ENABLED = os.environ.get("DISCORD_ENABLED", "false").lower() == "true"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
DISCORD_AVATAR_URL = os.environ.get("DISCORD_AVATAR_URL", "")

# Telegram Configuration
TELEGRAM_ENABLED = os.environ.get("TELEGRAM_ENABLED", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_PARSE_MODE = os.environ.get("TELEGRAM_PARSE_MODE", "HTML")

# Email Configuration
EMAIL_ENABLED = os.environ.get("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "")
EMAIL_SMTP_PORT = os.environ.get("EMAIL_SMTP_PORT", "587")
EMAIL_SMTP_USER = os.environ.get("EMAIL_SMTP_USER", "")
EMAIL_SMTP_PASSWORD = os.environ.get("EMAIL_SMTP_PASSWORD", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_TO = os.environ.get("EMAIL_TO", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "false").lower() == "true"
EMAIL_SUBJECT_PREFIX = os.environ.get("EMAIL_SUBJECT_PREFIX", "[WANwatcher]")

# General Configuration
IPINFO_TOKEN = os.environ.get("IPINFO_TOKEN", "")
IP_DB_FILE = os.environ.get("IP_DB_FILE", "/data/ipinfo.db")
LOG_FILE = os.environ.get("LOG_FILE", "/logs/wanwatcher.log")
BOT_NAME = os.environ.get("BOT_NAME", "WANwatcher")
SERVER_NAME = os.environ.get("SERVER_NAME", "WANwatcher Docker")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "900"))  # Default: 15 minutes

# IPv6 Configuration
MONITOR_IPV4 = os.environ.get("MONITOR_IPV4", "true").lower() == "true"
MONITOR_IPV6 = os.environ.get("MONITOR_IPV6", "true").lower() == "true"

# Update Check Configuration
UPDATE_CHECK_ENABLED = os.environ.get("UPDATE_CHECK_ENABLED", "true").lower() == "true"
UPDATE_CHECK_INTERVAL = int(
    os.environ.get("UPDATE_CHECK_INTERVAL", "86400")
)  # 24 hours
UPDATE_CHECK_ON_STARTUP = (
    os.environ.get("UPDATE_CHECK_ON_STARTUP", "true").lower() == "true"
)
GITHUB_API_URL = "https://api.github.com/repos/noxied/wanwatcher/releases/latest"
UPDATE_NOTIFIED_FILE = "/data/update_notified.txt"

# ============================================================================
# Setup Logging
# ============================================================================


def setup_logging() -> None:
    """Configure logging to file and console"""
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Configure logging with both file and console output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
    )


# ============================================================================
# IP Detection Functions
# ============================================================================


def get_ipv4_simple() -> Tuple[Optional[str], None]:
    """Get IPv4 address using simple services (no API key needed)"""
    services = [
        "https://api.ipify.org?format=json",
        "https://ipapi.co/json",
        "https://ifconfig.me/all.json",
        "https://api.myip.com",
    ]

    for service in services:
        try:
            logging.debug(f"Trying IP service: {service}")
            response = requests.get(service, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Different services use different keys
            ip = data.get("ip") or data.get("IPv4") or data.get("query")

            if ip and "." in ip:  # Simple IPv4 validation
                logging.debug(f"Successfully retrieved IPv4: {ip}")
                return ip, None
        except Exception as e:
            logging.warning(f"Failed to get IP from {service}: {e}")
            continue

    logging.warning("Failed to retrieve IPv4 from all services")
    return None, None


def get_ip_with_info() -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Get IPv4 with geographic information using ipinfo.io"""
    if not IPINFO_TOKEN:
        return get_ipv4_simple()

    try:
        import ipinfo

        handler = ipinfo.getHandler(IPINFO_TOKEN)
        details = handler.getDetails()

        geo_data = {
            "city": details.city,
            "region": details.region,
            "country": details.country_name,
            "org": details.org,
            "timezone": details.timezone,
        }

        logging.debug(f"Retrieved IP with geo data: {details.ip}")
        return details.ip, geo_data
    except ImportError:
        logging.debug("ipinfo module not installed, falling back to simple detection")
        return get_ipv4_simple()
    except Exception as e:
        logging.warning(f"ipinfo.io failed: {e}, falling back to simple detection")
        return get_ipv4_simple()


def is_valid_ipv6(ip_str: str) -> bool:
    """
    Validate if string is a valid IPv6 address.
    Excludes link-local and loopback addresses.
    """
    try:
        ip_obj = ipaddress.IPv6Address(ip_str)

        # Exclude special-use addresses
        if ip_obj.is_loopback:
            logging.debug(f"Rejected IPv6 (loopback): {ip_str}")
            return False

        if ip_obj.is_link_local:
            logging.debug(f"Rejected IPv6 (link-local): {ip_str}")
            return False

        if ip_obj.is_multicast:
            logging.debug(f"Rejected IPv6 (multicast): {ip_str}")
            return False

        if ip_obj.is_private:
            logging.debug(f"Rejected IPv6 (private): {ip_str}")
            return False

        if ip_obj.is_reserved:
            logging.debug(f"Rejected IPv6 (reserved): {ip_str}")
            return False

        # Valid global IPv6 address
        return True

    except (ipaddress.AddressValueError, ValueError):
        logging.debug(f"Invalid IPv6 format: {ip_str}")
        return False


def get_ipv6() -> Optional[str]:
    """Get IPv6 address from multiple services with proper validation"""
    services = [
        "https://api64.ipify.org?format=json",  # IPv6-specific service
        "https://api6.ipify.org?format=json",  # Another IPv6 service
        "https://v6.ident.me/.json",  # Alternative IPv6 service
    ]

    for service in services:
        try:
            logging.debug(f"Trying IPv6 service: {service}")
            response = requests.get(service, timeout=10)
            response.raise_for_status()

            # Handle JSON response
            data = response.json()
            ipv6 = data.get("ip", "") or data.get("address", "")

            # Properly validate IPv6 address
            if ipv6 and is_valid_ipv6(ipv6):
                logging.debug(f"Successfully retrieved and validated IPv6: {ipv6}")
                return ipv6
            else:
                logging.debug(f"Response was not a valid public IPv6: {ipv6}")

        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to get IPv6 from {service}: {e}")
            continue
        except Exception as e:
            logging.error(f"Unexpected error getting IPv6 from {service}: {e}")
            continue

    logging.warning("Failed to retrieve IPv6 from all services")
    return None


def get_current_ips() -> Tuple[Dict[str, Optional[str]], Optional[Dict[str, Any]]]:
    """
    Get both IPv4 and IPv6 addresses based on configuration.
    Returns dict: {'ipv4': '...', 'ipv6': '...'}, geo_data
    """
    logging.info("Detecting IP addresses...")

    result: Dict[str, Optional[str]] = {"ipv4": None, "ipv6": None}
    geo_data: Optional[Dict[str, Any]] = None

    # Get IPv4 if enabled
    if MONITOR_IPV4:
        result["ipv4"], geo_data = get_ip_with_info()
    else:
        logging.info("IPv4 monitoring disabled")

    # Get IPv6 if enabled
    if MONITOR_IPV6:
        result["ipv6"] = get_ipv6()
    else:
        logging.info("IPv6 monitoring disabled")

    logging.info(f"Detection complete - IPv4: {result['ipv4']}, IPv6: {result['ipv6']}")
    return result, geo_data


# ============================================================================
# IP Storage Functions
# ============================================================================


def ensure_db_dir() -> None:
    """Ensure the database directory exists"""
    db_dir = os.path.dirname(IP_DB_FILE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logging.info(f"Created database directory: {db_dir}")


def get_previous_ips() -> Dict[str, Optional[str]]:
    """
    Read previous IP addresses from database.
    Returns dict: {'ipv4': '...', 'ipv6': '...'}
    """
    if not os.path.exists(IP_DB_FILE):
        logging.info("No previous IP database found (first run)")
        return {"ipv4": None, "ipv6": None}

    try:
        with open(IP_DB_FILE, "r") as f:
            content = f.read().strip()

        # Try to parse as JSON (new format)
        try:
            data = json.loads(content)

            # Handle old format that was converted to JSON string
            if isinstance(data, str):
                logging.info("Converting old database format to new format")
                return {"ipv4": data, "ipv6": None}

            # New format (dict with both IPs)
            return {"ipv4": data.get("ipv4"), "ipv6": data.get("ipv6")}
        except json.JSONDecodeError:
            # Old format - plain text file with just IPv4
            logging.info("Converting legacy database format to new format")
            return {"ipv4": content, "ipv6": None}

    except Exception as e:
        logging.error(f"Error reading IP database: {e}")
        return {"ipv4": None, "ipv6": None}


def save_current_ips(ipv4: Optional[str], ipv6: Optional[str]) -> None:
    """Save current IP addresses to database"""
    try:
        ensure_db_dir()

        data = {"ipv4": ipv4, "ipv6": ipv6, "last_updated": datetime.now().isoformat()}

        with open(IP_DB_FILE, "w") as f:
            json.dump(data, f, indent=2)

        logging.debug(f"Saved IPs to database - IPv4: {ipv4}, IPv6: {ipv6}")

    except Exception as e:
        logging.error(f"Error saving IP database: {e}")
        raise


# ============================================================================
# Notification Setup
# ============================================================================

# Initialize notification manager (global)
notification_manager = NotificationManager()


def initialize_notifications() -> None:
    """Initialize all configured notification providers"""

    # Add Discord if configured
    if DISCORD_ENABLED and DISCORD_WEBHOOK_URL:
        discord = DiscordNotifier(DISCORD_WEBHOOK_URL, BOT_NAME, DISCORD_AVATAR_URL)
        notification_manager.add_provider(discord)
        logging.info("Discord notifications enabled")
    elif DISCORD_ENABLED and not DISCORD_WEBHOOK_URL:
        logging.warning("Discord enabled but DISCORD_WEBHOOK_URL not configured")

    # Add Telegram if configured
    if TELEGRAM_ENABLED and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        telegram = TelegramNotifier(
            TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_PARSE_MODE
        )
        notification_manager.add_provider(telegram)
        logging.info("Telegram notifications enabled")
    elif TELEGRAM_ENABLED and (not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID):
        logging.warning("Telegram enabled but BOT_TOKEN or CHAT_ID not configured")

    # Add Email if configured
    if EMAIL_ENABLED and all(
        [EMAIL_SMTP_HOST, EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]
    ):
        try:
            email_port = int(EMAIL_SMTP_PORT)
        except ValueError:
            logging.error(
                f"Invalid EMAIL_SMTP_PORT: {EMAIL_SMTP_PORT}, using default 587"
            )
            email_port = 587

        email = EmailNotifier(
            smtp_host=EMAIL_SMTP_HOST,
            smtp_port=email_port,
            smtp_user=EMAIL_SMTP_USER,
            smtp_password=EMAIL_SMTP_PASSWORD,
            from_addr=EMAIL_FROM,
            to_addrs=EMAIL_TO.split(","),
            use_tls=EMAIL_USE_TLS,
            use_ssl=EMAIL_USE_SSL,
            subject_prefix=EMAIL_SUBJECT_PREFIX,
        )
        notification_manager.add_provider(email)
        logging.info("Email notifications enabled")
    elif EMAIL_ENABLED:
        logging.warning(
            "Email enabled but missing required configuration (SMTP_HOST, SMTP_USER, SMTP_PASSWORD, FROM, or TO)"
        )

    if not notification_manager.providers:
        logging.warning("No notification providers configured!")


# ============================================================================
# Update Check Functions
# ============================================================================


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse version string to comparable tuple"""
    try:
        # Remove 'v' prefix and split by '.'
        parts = version_str.lstrip("v").split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        return (major, minor, patch)
    except:
        return (0, 0, 0)


def check_for_updates() -> Optional[Dict[str, str]]:
    """Check GitHub for newer version"""
    if not UPDATE_CHECK_ENABLED:
        return None

    try:
        logging.info("Checking for updates...")

        # Call GitHub API
        response = requests.get(GITHUB_API_URL, timeout=10)
        response.raise_for_status()
        release_data = response.json()

        latest_version = release_data.get("tag_name", "").lstrip("v")
        current_version = VERSION.lstrip("v")

        # Compare versions
        if parse_version(latest_version) > parse_version(current_version):
            logging.info(
                f"New version available: v{latest_version} (current: v{current_version})"
            )

            # Check if we already notified about this version
            if os.path.exists(UPDATE_NOTIFIED_FILE):
                with open(UPDATE_NOTIFIED_FILE, "r") as f:
                    notified_version = f.read().strip()
                    if notified_version == latest_version:
                        logging.info("Already notified about this version")
                        return None

            # Return update info
            return {
                "current_version": current_version,
                "latest_version": latest_version,
                "release_name": release_data.get("name", ""),
                "release_url": release_data.get("html_url", ""),
                "release_body": release_data.get("body", ""),
                "published_at": release_data.get("published_at", ""),
            }
        else:
            logging.info("WANwatcher is up to date")
            return None

    except Exception as e:
        logging.warning(f"Failed to check for updates: {e}")
        return None


def mark_update_notified(version: str) -> None:
    """Mark that we notified about this version"""
    try:
        with open(UPDATE_NOTIFIED_FILE, "w") as f:
            f.write(version)
        logging.debug(f"Marked update v{version} as notified")
    except Exception as e:
        logging.error(f"Failed to save update notification state: {e}")


def send_update_notification(update_info: Dict[str, str]) -> None:
    """Send update notification to all platforms"""
    try:
        logging.info(
            f"Sending update notification for v{update_info['latest_version']}"
        )

        # Notify via all configured platforms
        results = notification_manager.notify_update(update_info, SERVER_NAME, VERSION)

        # Log results
        for provider, success in results.items():
            if success:
                logging.info(f"{provider} update notification sent successfully")
            else:
                logging.warning(f"{provider} update notification failed")

        # Mark as notified if at least one succeeded
        if any(results.values()):
            mark_update_notified(update_info["latest_version"])

    except Exception as e:
        logging.error(f"Failed to send update notification: {e}")


# ============================================================================
# Main Check Function
# ============================================================================


def check_ip() -> bool:
    """Perform single IP check"""
    try:
        # Get current IPs
        current_ips, geo_data = get_current_ips()

        # Verify we got at least one IP
        if not current_ips["ipv4"] and not current_ips["ipv6"]:
            logging.error("Failed to retrieve any IP address!")
            raise Exception("No IP addresses detected")

        logging.info(
            f"Current IPv4: {current_ips['ipv4']}, IPv6: {current_ips['ipv6']}"
        )

        # Get previous IPs
        previous_ips = get_previous_ips()
        is_first_run = previous_ips["ipv4"] is None and previous_ips["ipv6"] is None

        # Check if anything changed
        ipv4_changed = current_ips["ipv4"] != previous_ips["ipv4"]
        ipv6_changed = current_ips["ipv6"] != previous_ips["ipv6"]

        if is_first_run:
            logging.info("First run detected - sending initial notification")
            notification_manager.notify_all(
                current_ips, previous_ips, geo_data, True, SERVER_NAME, VERSION
            )
            save_current_ips(current_ips["ipv4"], current_ips["ipv6"])

        elif ipv4_changed or ipv6_changed:
            change_msgs = []
            if ipv4_changed:
                change_msgs.append(
                    f"IPv4: {previous_ips['ipv4']} → {current_ips['ipv4']}"
                )
            if ipv6_changed:
                change_msgs.append(
                    f"IPv6: {previous_ips['ipv6']} → {current_ips['ipv6']}"
                )

            logging.warning("IP ADDRESS CHANGE DETECTED!")
            for msg in change_msgs:
                logging.warning(f"  {msg}")

            notification_manager.notify_all(
                current_ips, previous_ips, geo_data, False, SERVER_NAME, VERSION
            )
            save_current_ips(current_ips["ipv4"], current_ips["ipv6"])

        else:
            logging.info("No IP address changes detected")

        return True

    except Exception as e:
        error_msg = f"Error during IP check: {str(e)}"
        logging.error(error_msg, exc_info=True)
        notification_manager.notify_error(error_msg, SERVER_NAME)
        return False


# ============================================================================
# Main Loop for Docker
# ============================================================================


def main() -> None:
    """Main execution function with continuous loop"""
    setup_logging()

    logging.info("=" * 60)
    logging.info(f"WANwatcher v{VERSION} Docker started")
    logging.info(f"Server Name: {SERVER_NAME}")
    logging.info(
        f"Check Interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//60} minutes)"
    )
    logging.info(f"IPv4 Monitoring: {'Enabled' if MONITOR_IPV4 else 'Disabled'}")
    logging.info(f"IPv6 Monitoring: {'Enabled' if MONITOR_IPV6 else 'Disabled'}")
    logging.info("=" * 60)

    # Validate configuration
    logging.info("Validating configuration...")
    if not validate_config():
        logging.error("Configuration validation failed - exiting")
        sys.exit(1)
    logging.info("Configuration validation passed")

    # Initialize notifications
    initialize_notifications()

    logging.info("Notification Status:")

    # Discord status
    if DISCORD_ENABLED and DISCORD_WEBHOOK_URL:
        logging.info(f"  Discord: Configured ✓")
    elif DISCORD_ENABLED:
        logging.warning(f"  Discord: Enabled but WEBHOOK_URL missing ✗")
    else:
        logging.info(f"  Discord: Not enabled")

    # Telegram status
    if TELEGRAM_ENABLED and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        logging.info(f"  Telegram: Configured ✓")
    elif TELEGRAM_ENABLED:
        logging.warning(f"  Telegram: Enabled but BOT_TOKEN or CHAT_ID missing ✗")
    else:
        logging.info(f"  Telegram: Not enabled")

    # Email status
    if EMAIL_ENABLED and all(
        [EMAIL_SMTP_HOST, EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]
    ):
        logging.info(f"  Email: Configured ✓")
    elif EMAIL_ENABLED:
        logging.warning(f"  Email: Enabled but missing SMTP configuration ✗")
    else:
        logging.info(f"  Email: Not enabled")

    logging.info(
        f"  ipinfo.io: {'Configured' if IPINFO_TOKEN else 'Not configured (geo data disabled)'}"
    )
    logging.info(f"  Update Check: {'Enabled' if UPDATE_CHECK_ENABLED else 'Disabled'}")
    logging.info("=" * 60)

    # Validation
    if not notification_manager.providers:
        logging.error("FATAL: No notification providers configured!")
        logging.error("Please enable and configure at least one notification method:")
        logging.error("  - Discord: Set DISCORD_ENABLED=true and DISCORD_WEBHOOK_URL")
        logging.error(
            "  - Telegram: Set TELEGRAM_ENABLED=true, TELEGRAM_BOT_TOKEN, and TELEGRAM_CHAT_ID"
        )
        logging.error(
            "  - Email: Set EMAIL_ENABLED=true and all required SMTP settings"
        )
        sys.exit(1)

    if not MONITOR_IPV4 and not MONITOR_IPV6:
        logging.error("FATAL: Both IPv4 and IPv6 monitoring are disabled!")
        logging.error("Please enable at least one protocol")
        sys.exit(1)

    # Check for updates on startup
    if UPDATE_CHECK_ON_STARTUP:
        update_info = check_for_updates()
        if update_info:
            send_update_notification(update_info)

    # Initial check
    logging.info("Performing initial IP check...")
    check_ip()

    # Continuous monitoring loop
    logging.info(
        f"Starting continuous monitoring (checking every {CHECK_INTERVAL} seconds)..."
    )

    check_count = 0
    last_update_check = datetime.now()

    while True:
        try:
            time.sleep(CHECK_INTERVAL)
            check_count += 1
            logging.info(f"Performing check #{check_count}...")
            check_ip()

            # Periodic update check
            if UPDATE_CHECK_ENABLED:
                from datetime import timedelta

                time_since_check = (datetime.now() - last_update_check).total_seconds()
                if time_since_check >= UPDATE_CHECK_INTERVAL:
                    logging.debug(
                        f"Periodic update check (interval: {UPDATE_CHECK_INTERVAL}s)"
                    )
                    update_info = check_for_updates()
                    if update_info:
                        send_update_notification(update_info)
                    last_update_check = datetime.now()

        except KeyboardInterrupt:
            logging.info("Received shutdown signal, stopping WANwatcher...")
            break
        except Exception as e:
            logging.error(f"Unexpected error in main loop: {e}", exc_info=True)
            notification_manager.notify_error(f"Main loop error: {str(e)}", SERVER_NAME)
            # Wait a bit before retrying
            time.sleep(60)


if __name__ == "__main__":
    main()
