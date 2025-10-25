#!/usr/bin/env python3
"""
WANwatcher Docker - WAN IP Address Monitor with Discord Notifications
Docker-optimized version with continuous loop mode

Features:
- Automatic IP change detection
- Discord webhook notifications with rich embeds
- Detailed logging
- Error handling and recovery
- Supports multiple IP detection services as fallback
- Optional ipinfo.io integration for geographic data
- Continuous monitoring mode for Docker
"""

import requests
import json
import os
import sys
import logging
import time
from datetime import datetime

# ============================================================================
# CONFIGURATION - Loaded from Environment Variables
# ============================================================================

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')
IPINFO_TOKEN = os.environ.get('IPINFO_TOKEN', '')
IP_DB_FILE = os.environ.get('IP_DB_FILE', '/data/ipinfo.db')
LOG_FILE = os.environ.get('LOG_FILE', '/logs/wanwatcher.log')
BOT_NAME = os.environ.get('BOT_NAME', 'WANwatcher')
SERVER_NAME = os.environ.get('SERVER_NAME', 'WANwatcher Docker')
CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', '900'))  # Default: 15 minutes

# IPv6 Configuration
MONITOR_IPV4 = os.environ.get('MONITOR_IPV4', 'true').lower() == 'true'
MONITOR_IPV6 = os.environ.get('MONITOR_IPV6', 'true').lower() == 'true'

# ============================================================================
# Setup Logging
# ============================================================================

def setup_logging():
    """Configure logging to file and console"""
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging with both file and console output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

# ============================================================================
# IP Detection Functions
# ============================================================================

def get_ipv4_simple():
    """Get IPv4 address using simple services (no API key needed)"""
    services = [
        "https://api.ipify.org?format=json",
        "https://ipapi.co/json",
        "https://ifconfig.me/all.json",
        "https://api.myip.com"
    ]
    
    for service in services:
        try:
            logging.debug(f"Trying IP service: {service}")
            response = requests.get(service, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Different services use different keys
            ip = data.get('ip') or data.get('IPv4') or data.get('query')
            
            if ip and '.' in ip:  # Simple IPv4 validation
                logging.debug(f"Successfully retrieved IPv4: {ip}")
                return ip, None
        except Exception as e:
            logging.warning(f"Failed to get IP from {service}: {e}")
            continue
    
    logging.warning("Failed to retrieve IPv4 from all services")
    return None, None

def get_ip_with_info():
    """Get IPv4 with geographic information using ipinfo.io"""
    if not IPINFO_TOKEN:
        return get_ipv4_simple()
    
    try:
        import ipinfo
        handler = ipinfo.getHandler(IPINFO_TOKEN)
        details = handler.getDetails()
        
        geo_data = {
            'city': details.city,
            'region': details.region,
            'country': details.country_name,
            'org': details.org,
            'timezone': details.timezone
        }
        
        logging.debug(f"Retrieved IP with geo data: {details.ip}")
        return details.ip, geo_data
    except ImportError:
        logging.debug("ipinfo module not installed, falling back to simple detection")
        return get_ipv4_simple()
    except Exception as e:
        logging.warning(f"ipinfo.io failed: {e}, falling back to simple detection")
        return get_ipv4_simple()
        
def get_ipv6():
    """Get IPv6 address from multiple services"""
    services = [
        'https://api64.ipify.org?format=json',  # IPv6-specific service
        'https://api6.ipify.org?format=json',   # Another IPv6 service
    ]
    
    for service in services:
        try:
            logging.debug(f"Trying IPv6 service: {service}")
            response = requests.get(service, timeout=10)
            response.raise_for_status()
            
            # Handle JSON response
            data = response.json()
            ipv6 = data.get('ip', '')
            
            # Validate it's actually IPv6 (contains colons)
            if ipv6 and ':' in ipv6:
                logging.debug(f"Successfully retrieved IPv6: {ipv6}")
                return ipv6
            else:
                logging.debug(f"Response was not IPv6: {ipv6}")
                
        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to get IPv6 from {service}: {e}")
            continue
        except Exception as e:
            logging.error(f"Unexpected error getting IPv6 from {service}: {e}")
            continue
    
    logging.warning("Failed to retrieve IPv6 from all services")
    return None
    
def get_current_ips():
    """
    Get both IPv4 and IPv6 addresses based on configuration.
    Returns dict: {'ipv4': '...', 'ipv6': '...'}, geo_data
    """
    logging.info("Detecting IP addresses...")
    
    result = {'ipv4': None, 'ipv6': None}
    geo_data = None
    
    # Get IPv4 if enabled
    if MONITOR_IPV4:
        result['ipv4'], geo_data = get_ip_with_info()
    else:
        logging.info("IPv4 monitoring disabled")
    
    # Get IPv6 if enabled
    if MONITOR_IPV6:
        result['ipv6'] = get_ipv6()
    else:
        logging.info("IPv6 monitoring disabled")
    
    logging.info(f"Detection complete - IPv4: {result['ipv4']}, IPv6: {result['ipv6']}")
    return result, geo_data

# ============================================================================
# IP Storage Functions
# ============================================================================

def ensure_db_dir():
    """Ensure the database directory exists"""
    db_dir = os.path.dirname(IP_DB_FILE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logging.info(f"Created database directory: {db_dir}")

def get_previous_ips():
    """
    Read previous IP addresses from database.
    Returns dict: {'ipv4': '...', 'ipv6': '...'}
    """
    if not os.path.exists(IP_DB_FILE):
        logging.info("No previous IP database found (first run)")
        return {'ipv4': None, 'ipv6': None}
    
    try:
        with open(IP_DB_FILE, 'r') as f:
            content = f.read().strip()
            
        # Try to parse as JSON (new format)
        try:
            data = json.loads(content)
            
            # Handle old format that was converted to JSON string
            if isinstance(data, str):
                logging.info("Converting old database format to new format")
                return {'ipv4': data, 'ipv6': None}
            
            # New format (dict with both IPs)
            return {
                'ipv4': data.get('ipv4'),
                'ipv6': data.get('ipv6')
            }
        except json.JSONDecodeError:
            # Old format - plain text file with just IPv4
            logging.info("Converting legacy database format to new format")
            return {'ipv4': content, 'ipv6': None}
            
    except Exception as e:
        logging.error(f"Error reading IP database: {e}")
        return {'ipv4': None, 'ipv6': None}

def save_current_ips(ipv4, ipv6):
    """Save current IP addresses to database"""
    try:
        ensure_db_dir()
        
        data = {
            'ipv4': ipv4,
            'ipv6': ipv6,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(IP_DB_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        logging.debug(f"Saved IPs to database - IPv4: {ipv4}, IPv6: {ipv6}")
        
    except Exception as e:
        logging.error(f"Error saving IP database: {e}")
        raise

# ============================================================================
# Discord Notification Functions
# ============================================================================

def send_discord_notification(current_ips, previous_ips, geo_data=None, is_first_run=False):
    """Send rich embed notification to Discord with both IPv4 and IPv6"""
    
    if not DISCORD_WEBHOOK_URL:
        logging.error("DISCORD_WEBHOOK_URL not set!")
        return False
    
    # Determine what changed
    ipv4_changed = current_ips['ipv4'] != previous_ips['ipv4']
    ipv6_changed = current_ips['ipv6'] != previous_ips['ipv6']
    
    # Build title and description based on what changed
    if is_first_run:
        title = "🟢 Initial IP Detection"
        description = f"Monitoring started for **{SERVER_NAME}**"
        color = 3066993  # Green
    elif ipv4_changed and ipv6_changed:
        title = "🔄 Both IP Addresses Changed"
        description = f"IPv4 and IPv6 for **{SERVER_NAME}** have been updated"
        color = 15844367  # Gold/Orange
    elif ipv4_changed:
        title = "🔄 IPv4 Address Changed"
        description = f"IPv4 for **{SERVER_NAME}** has been updated"
        color = 15844367  # Gold/Orange
    elif ipv6_changed:
        title = "🔄 IPv6 Address Changed"
        description = f"IPv6 for **{SERVER_NAME}** has been updated"
        color = 15844367  # Gold/Orange
    else:
        # No changes (shouldn't happen but handle it)
        title = "✅ IP Status Update"
        description = f"IP addresses confirmed for **{SERVER_NAME}**"
        color = 3066993  # Green
    
    # Build fields
    fields = []
    
    # IPv4 section
    if current_ips['ipv4']:
        fields.append({
            "name": "📍 Current IPv4",
            "value": f"`{current_ips['ipv4']}`",
            "inline": True
        })
        if previous_ips['ipv4'] and ipv4_changed and not is_first_run:
            fields.append({
                "name": "📌 Previous IPv4",
                "value": f"`{previous_ips['ipv4']}`",
                "inline": True
            })
    
    # Add spacer for better layout
    if current_ips['ipv4'] and current_ips['ipv6']:
        fields.append({"name": "\u200b", "value": "\u200b", "inline": False})
    
    # IPv6 section
    if current_ips['ipv6']:
        fields.append({
            "name": "📍 Current IPv6",
            "value": f"`{current_ips['ipv6']}`",
            "inline": False  # IPv6 addresses are long
        })
        if previous_ips['ipv6'] and ipv6_changed and not is_first_run:
            fields.append({
                "name": "📌 Previous IPv6",
                "value": f"`{previous_ips['ipv6']}`",
                "inline": False
            })
    elif current_ips['ipv4']:  # Only IPv4 available
        fields.append({
            "name": "ℹ️ IPv6 Status",
            "value": "Not available or not configured",
            "inline": False
        })
    
    # Add spacer before geo data
    fields.append({"name": "\u200b", "value": "\u200b", "inline": False})
    
    # Add geographic information if available
    if geo_data:
        geo_text = f"🌍 {geo_data.get('city', 'Unknown')}, {geo_data.get('region', '')}, {geo_data.get('country', 'Unknown')}\n"
        geo_text += f"🏢 {geo_data.get('org', 'Unknown ISP')}\n"
        geo_text += f"🕐 {geo_data.get('timezone', 'Unknown')}"
        
        fields.append({
            "name": "📍 Location Information",
            "value": geo_text,
            "inline": False
        })
    
    # Add timestamp (using Discord timestamp format)
    local_timestamp = int(datetime.now().timestamp())
    fields.append({
        "name": "⏰ Detected At",
        "value": f"<t:{local_timestamp}:F>",
        "inline": False
    })
    
    # Add Docker info
    fields.append({
        "name": "🐳 Environment",
        "value": "Running in Docker",
        "inline": True
    })
    
    # Build embed
    embed = {
        "title": f"🌐 {title}",
        "description": description,
        "color": color,
        "fields": fields,
        "footer": {
            "text": f"WANwatcher on {SERVER_NAME}"
        },
        "timestamp": datetime.now().astimezone().isoformat()
    }
    
    # Build payload
    payload = {
        "username": BOT_NAME,
        "embeds": [embed]
    }
    
    # Send to Discord
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        logging.info(f"Discord notification sent successfully (Status: {response.status_code})")
        return True
    except Exception as e:
        logging.error(f"Failed to send Discord notification: {e}")
        return False

def send_error_notification(error_message):
    """Send error notification to Discord"""
    if not DISCORD_WEBHOOK_URL:
        return
        
    payload = {
        "username": BOT_NAME,
        "embeds": [{
            "title": "⚠️ WANwatcher Error",
            "description": f"An error occurred on {SERVER_NAME}",
            "color": 15158332,  # Red
            "fields": [
                {
                    "name": "Error Details",
                    "value": f"```{error_message[:1000]}```",  # Limit to 1000 chars
                    "inline": False
                },
                {
                    "name": "🐳 Environment",
                    "value": "Running in Docker",
                    "inline": True
                }
            ],
            "footer": {
                "text": f"WANwatcher on {SERVER_NAME}"
            },
            "timestamp": datetime.now().astimezone().isoformat()
        }]
    }
    
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
    except:
        pass  # Don't fail if error notification fails

# ============================================================================
# Main Check Function
# ============================================================================

def check_ip():
    """Perform single IP check"""
    try:
        # Get current IPs
        current_ips, geo_data = get_current_ips()
        
        # Verify we got at least one IP
        if not current_ips['ipv4'] and not current_ips['ipv6']:
            logging.error("Failed to retrieve any IP address!")
            raise Exception("No IP addresses detected")
        
        logging.info(f"Current IPv4: {current_ips['ipv4']}, IPv6: {current_ips['ipv6']}")
        
        # Get previous IPs
        previous_ips = get_previous_ips()
        is_first_run = (previous_ips['ipv4'] is None and previous_ips['ipv6'] is None)
        
        # Check if anything changed
        ipv4_changed = current_ips['ipv4'] != previous_ips['ipv4']
        ipv6_changed = current_ips['ipv6'] != previous_ips['ipv6']
        
        if is_first_run:
            logging.info("First run detected - sending initial notification")
            send_discord_notification(current_ips, previous_ips, geo_data, is_first_run=True)
            save_current_ips(current_ips['ipv4'], current_ips['ipv6'])
            
        elif ipv4_changed or ipv6_changed:
            change_msgs = []
            if ipv4_changed:
                change_msgs.append(f"IPv4: {previous_ips['ipv4']} → {current_ips['ipv4']}")
            if ipv6_changed:
                change_msgs.append(f"IPv6: {previous_ips['ipv6']} → {current_ips['ipv6']}")
            
            logging.warning("IP ADDRESS CHANGE DETECTED!")
            for msg in change_msgs:
                logging.warning(f"  {msg}")
            
            send_discord_notification(current_ips, previous_ips, geo_data, is_first_run=False)
            save_current_ips(current_ips['ipv4'], current_ips['ipv6'])
            
        else:
            logging.info("No IP address changes detected")
        
        return True
        
    except Exception as e:
        error_msg = f"Error during IP check: {str(e)}"
        logging.error(error_msg, exc_info=True)
        send_error_notification(error_msg)
        return False

# ============================================================================
# Main Loop for Docker
# ============================================================================

def main():
    """Main execution function with continuous loop"""
    setup_logging()
    
    logging.info("=" * 60)
    logging.info("WANwatcher Docker started (with IPv6 support)")
    logging.info(f"Server Name: {SERVER_NAME}")
    logging.info(f"Check Interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//60} minutes)")
    logging.info(f"Discord Webhook: {'Configured' if DISCORD_WEBHOOK_URL else 'NOT SET!'}")
    logging.info(f"ipinfo.io Token: {'Configured' if IPINFO_TOKEN else 'Not configured (geo data disabled)'}")
    logging.info(f"IPv4 Monitoring: {'Enabled' if MONITOR_IPV4 else 'Disabled'}")
    logging.info(f"IPv6 Monitoring: {'Enabled' if MONITOR_IPV6 else 'Disabled'}")
    logging.info("=" * 60)
    
    if not DISCORD_WEBHOOK_URL:
        logging.error("FATAL: DISCORD_WEBHOOK_URL environment variable is not set!")
        logging.error("Please set DISCORD_WEBHOOK_URL before running the container")
        sys.exit(1)
    
    if not MONITOR_IPV4 and not MONITOR_IPV6:
        logging.error("FATAL: Both IPv4 and IPv6 monitoring are disabled!")
        logging.error("Please enable at least one protocol")
        sys.exit(1)
    
    # Initial check
    logging.info("Performing initial IP check...")
    check_ip()
    
    # Continuous monitoring loop
    logging.info(f"Starting continuous monitoring (checking every {CHECK_INTERVAL} seconds)...")
    
    check_count = 0
    while True:
        try:
            time.sleep(CHECK_INTERVAL)
            check_count += 1
            logging.info(f"Performing check #{check_count}...")
            check_ip()
            
        except KeyboardInterrupt:
            logging.info("Received shutdown signal, stopping WANwatcher...")
            break
        except Exception as e:
            logging.error(f"Unexpected error in main loop: {e}", exc_info=True)
            send_error_notification(f"Main loop error: {str(e)}")
            # Wait a bit before retrying
            time.sleep(60)

if __name__ == "__main__":
    main()
