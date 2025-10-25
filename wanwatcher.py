#!/usr/bin/env python3
"""
WANwatcher - WAN IP Address Monitor with Discord Notifications
Monitors your WAN IP address and sends notifications to Discord when it changes.

Features:
- Automatic IP change detection (IPv4 and IPv6)
- Discord webhook notifications with rich embeds
- Detailed logging
- Error handling and recovery
- Supports multiple IP detection services as fallback
- Optional ipinfo.io integration for geographic data
- Dual-stack network support
"""

import requests
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# ============================================================================
# CONFIGURATION - Edit these values
# ============================================================================

# Discord Webhook URL (Required)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"

# ipinfo.io API Token (Optional - for geographic information)
# Get free token at: https://ipinfo.io/signup
IPINFO_TOKEN = ""  # Leave empty if you don't want geo data

# File to store the last known IP
IP_DB_FILE = "/var/lib/wanwatcher/ipinfo.db"

# Log file location
LOG_FILE = "/var/log/wanwatcher.log"

# Discord bot name
BOT_NAME = "WANwatcher"

# Server/Location name (will appear in Discord message)
SERVER_NAME = "HPE DL380 G9 Lab"

# IPv6 Configuration
MONITOR_IPV4 = True
MONITOR_IPV6 = True

# ============================================================================
# Setup Logging
# ============================================================================

def setup_logging():
    """Configure logging to file and console"""
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
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
            logging.info(f"Trying IPv4 service: {service}")
            response = requests.get(service, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Different services use different keys
            ip = data.get('ip') or data.get('IPv4') or data.get('query')
            
            if ip and '.' in ip:  # Simple IPv4 validation
                logging.info(f"Successfully retrieved IPv4: {ip}")
                return ip, None
        except Exception as e:
            logging.warning(f"Failed to get IPv4 from {service}: {e}")
            continue
    
    logging.warning("Failed to retrieve IPv4 from all services")
    return None, None

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
        
        logging.info(f"Retrieved IP with geo data: {details.ip}")
        return details.ip, geo_data
    except ImportError:
        logging.warning("ipinfo module not installed, falling back to simple detection")
        return get_ipv4_simple()
    except Exception as e:
        logging.warning(f"ipinfo.io failed: {e}, falling back to simple detection")
        return get_ipv4_simple()

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
        
        logging.info(f"Saved IPs to database - IPv4: {ipv4}, IPv6: {ipv6}")
        
    except Exception as e:
        logging.error(f"Error saving IP database: {e}")
        raise

# ============================================================================
# Discord Notification Functions
# ============================================================================

def send_discord_notification(current_ips, previous_ips, geo_data=None, is_first_run=False):
    """Send rich embed notification to Discord with both IPv4 and IPv6"""
    
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
    
    # Add timestamp
    fields.append({
        "name": "⏰ Detected At",
        "value": f"<t:{int(datetime.utcnow().timestamp())}:F>",
        "inline": False
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
        "timestamp": datetime.utcnow().isoformat()
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
    payload = {
        "username": BOT_NAME,
        "embeds": [{
            "title": "⚠️ WANwatcher Error",
            "description": f"An error occurred on {SERVER_NAME}",
            "color": 15158332,  # Red
            "fields": [
                {
                    "name": "Error Details",
                    "value": f"```{error_message}```",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"WANwatcher on {SERVER_NAME}"
            },
            "timestamp": datetime.utcnow().isoformat()
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
# Main Function
# ============================================================================

def main():
    """Main execution function"""
    setup_logging()
    logging.info("=" * 60)
    logging.info("WANwatcher started (with IPv6 support)")
    logging.info(f"IPv4 Monitoring: {MONITOR_IPV4}")
    logging.info(f"IPv6 Monitoring: {MONITOR_IPV6}")
    logging.info("=" * 60)
    
    if not MONITOR_IPV4 and not MONITOR_IPV6:
        logging.error("FATAL: Both IPv4 and IPv6 monitoring are disabled!")
        logging.error("Please enable at least one protocol")
        sys.exit(1)
    
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
        
        logging.info("WANwatcher completed successfully")
        return 0
        
    except Exception as e:
        error_msg = f"Fatal error: {str(e)}"
        logging.error(error_msg, exc_info=True)
        send_error_notification(error_msg)
        return 1

if __name__ == "__main__":
    sys.exit(main())
