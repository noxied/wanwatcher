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
            logging.debug(f"Trying IP service: {service}")
            response = requests.get(service, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Different services use different keys
            ip = data.get('ip') or data.get('IPv4') or data.get('query')
            
            if ip:
                logging.debug(f"Successfully retrieved IP: {ip}")
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
        
        logging.debug(f"Retrieved IP with geo data: {details.ip}")
        return details.ip, geo_data
    except ImportError:
        logging.debug("ipinfo module not installed, falling back to simple detection")
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
                logging.debug(f"Previous IP: {previous_ip}")
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
        logging.debug(f"Saved current IP: {ip}")
    except Exception as e:
        logging.error(f"Error saving IP: {e}")
        raise

# ============================================================================
# Discord Notification Functions
# ============================================================================

def send_discord_notification(ip, previous_ip, geo_data=None, is_first_run=False):
    """Send rich embed notification to Discord"""
    
    if not DISCORD_WEBHOOK_URL:
        logging.error("DISCORD_WEBHOOK_URL not set!")
        return False
    
    timestamp = datetime.now().astimezone().isoformat()
    
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
    
    # Add timestamp (using local time)
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
        "title": "🌐 WAN IP Monitor Alert",
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
    logging.info("WANwatcher Docker started")
    logging.info(f"Server Name: {SERVER_NAME}")
    logging.info(f"Check Interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//60} minutes)")
    logging.info(f"Discord Webhook: {'Configured' if DISCORD_WEBHOOK_URL else 'NOT SET!'}")
    logging.info(f"ipinfo.io Token: {'Configured' if IPINFO_TOKEN else 'Not configured (geo data disabled)'}")
    logging.info("=" * 60)
    
    if not DISCORD_WEBHOOK_URL:
        logging.error("FATAL: DISCORD_WEBHOOK_URL environment variable is not set!")
        logging.error("Please set DISCORD_WEBHOOK_URL before running the container")
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
