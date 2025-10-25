#!/usr/bin/env python3
"""
WANwatcher - WAN IP Address Monitor with Discord Notifications
Monitors your WAN IP address and sends notifications to Discord when it changes.

Features:
- Automatic IP change detection
- Discord webhook notifications with rich embeds
- Detailed logging
- Error handling and recovery
- Supports multiple IP detection services as fallback
- Optional ipinfo.io integration for geographic data
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

def get_ip_simple():
    """Get WAN IP using simple services (no API key needed)"""
    services = [
        "https://api.ipify.org?format=json",
        "https://ipapi.co/json",
        "https://ifconfig.me/all.json",
        "https://api.myip.com"
    ]
    
    for service in services:
        try:
            logging.info(f"Trying IP service: {service}")
            response = requests.get(service, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Different services use different keys
            ip = data.get('ip') or data.get('IPv4') or data.get('query')
            
            if ip:
                logging.info(f"Successfully retrieved IP: {ip}")
                return ip, None
        except Exception as e:
            logging.warning(f"Failed to get IP from {service}: {e}")
            continue
    
    raise Exception("Failed to retrieve IP from all services")

def get_ip_with_info():
    """Get WAN IP with geographic information using ipinfo.io"""
    if not IPINFO_TOKEN:
        return get_ip_simple()
    
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
        return get_ip_simple()
    except Exception as e:
        logging.warning(f"ipinfo.io failed: {e}, falling back to simple detection")
        return get_ip_simple()

# ============================================================================
# IP Storage Functions
# ============================================================================

def ensure_db_dir():
    """Ensure the database directory exists"""
    db_dir = os.path.dirname(IP_DB_FILE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logging.info(f"Created database directory: {db_dir}")

def get_previous_ip():
    """Read the previous IP from database file"""
    try:
        if os.path.exists(IP_DB_FILE):
            with open(IP_DB_FILE, 'r') as f:
                previous_ip = f.read().strip()
                logging.info(f"Previous IP: {previous_ip}")
                return previous_ip
        else:
            logging.info("No previous IP found (first run)")
            return None
    except Exception as e:
        logging.error(f"Error reading previous IP: {e}")
        return None

def save_current_ip(ip):
    """Save current IP to database file"""
    try:
        ensure_db_dir()
        with open(IP_DB_FILE, 'w') as f:
            f.write(ip)
        logging.info(f"Saved current IP: {ip}")
    except Exception as e:
        logging.error(f"Error saving IP: {e}")
        raise

# ============================================================================
# Discord Notification Functions
# ============================================================================

def send_discord_notification(ip, previous_ip, geo_data=None, is_first_run=False):
    """Send rich embed notification to Discord"""
    
    timestamp = datetime.utcnow().isoformat()
    
    # Build description
    if is_first_run:
        description = f"🟢 **Initial IP Detection**\nMonitoring started for {SERVER_NAME}"
        color = 3066993  # Green
    else:
        description = f"🔄 **IP Address Changed**\nWAN IP for {SERVER_NAME} has been updated"
        color = 15844367  # Gold/Orange
    
    # Build embed fields
    fields = [
        {
            "name": "📍 Current IP",
            "value": f"`{ip}`",
            "inline": True
        }
    ]
    
    if previous_ip and not is_first_run:
        fields.append({
            "name": "📌 Previous IP",
            "value": f"`{previous_ip}`",
            "inline": True
        })
    
    # Add geographic information if available
    if geo_data:
        geo_text = f"🌍 {geo_data.get('city', 'Unknown')}, {geo_data.get('region', '')}, {geo_data.get('country', 'Unknown')}\n"
        geo_text += f"🏢 {geo_data.get('org', 'Unknown ISP')}\n"
        geo_text += f"🕐 {geo_data.get('timezone', 'Unknown')}"
        
        fields.append({
            "name": "Location Information",
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
        "title": "🌐 WAN IP Monitor Alert",
        "description": description,
        "color": color,
        "fields": fields,
        "footer": {
            "text": f"WANwatcher on {SERVER_NAME}"
        },
        "timestamp": timestamp
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
    logging.info("WANwatcher started")
    logging.info("=" * 60)
    
    try:
        # Get current IP
        current_ip, geo_data = get_ip_with_info()
        logging.info(f"Current WAN IP: {current_ip}")
        
        # Get previous IP
        previous_ip = get_previous_ip()
        is_first_run = previous_ip is None
        
        # Check if IP changed
        if current_ip != previous_ip:
            if is_first_run:
                logging.info("First run detected - sending initial notification")
            else:
                logging.info(f"IP CHANGED! {previous_ip} → {current_ip}")
            
            # Send Discord notification
            send_discord_notification(
                current_ip,
                previous_ip,
                geo_data,
                is_first_run=is_first_run
            )
            
            # Save new IP
            save_current_ip(current_ip)
        else:
            logging.info("IP address unchanged - no notification sent")
        
        logging.info("WANwatcher completed successfully")
        return 0
        
    except Exception as e:
        error_msg = f"Fatal error: {str(e)}"
        logging.error(error_msg, exc_info=True)
        send_error_notification(error_msg)
        return 1

if __name__ == "__main__":
    sys.exit(main())
