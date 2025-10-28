#!/usr/bin/env python3
"""
WANwatcher - WAN IP Monitor with Multi-Platform Notifications
Monitors WAN IP changes and sends notifications via Email, Telegram, and Discord
"""

import os
import time
import requests
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Version
VERSION = "1.3.0"

# Configuration from environment variables
SERVER_NAME = os.getenv('SERVER_NAME', 'Server')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '900'))  # 15 minutes default

# Email configuration
ENABLE_EMAIL = os.getenv('ENABLE_EMAIL', 'false').lower() == 'true'
SMTP_SERVER = os.getenv('SMTP_SERVER', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
EMAIL_FROM = os.getenv('EMAIL_FROM', '')
EMAIL_TO = os.getenv('EMAIL_TO', '')

# Telegram configuration
ENABLE_TELEGRAM = os.getenv('ENABLE_TELEGRAM', 'false').lower() == 'true'
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', ''

)

# Discord configuration
ENABLE_DISCORD = os.getenv('ENABLE_DISCORD', 'false').lower() == 'true'
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

# State file
STATE_FILE = '/data/last_ip.txt'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_wan_ip():
    """Fetch current WAN IP address"""
    services = [
        'https://api.ipify.org',
        'https://ifconfig.me/ip',
        'https://icanhazip.com'
    ]
    
    for service in services:
        try:
            response = requests.get(service, timeout=10)
            if response.status_code == 200:
                return response.text.strip()
        except Exception as e:
            logging.warning(f"Failed to get IP from {service}: {e}")
            continue
    
    raise Exception("Could not retrieve WAN IP from any service")

def read_last_ip():
    """Read the last known IP from state file"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return f.read().strip()
    except Exception as e:
        logging.error(f"Error reading state file: {e}")
    return None

def write_last_ip(ip):
    """Write the current IP to state file"""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            f.write(ip)
    except Exception as e:
        logging.error(f"Error writing state file: {e}")

def send_email(subject, body):
    """Send email notification"""
    if not ENABLE_EMAIL:
        return
    
    # Check if all required email settings are configured
    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        logging.error("Email enabled but missing required configuration (SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, or EMAIL_TO)")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logging.info(f"Email notification sent successfully to {EMAIL_TO}")
    except Exception as e:
        logging.error(f"Email notification failed: {e}")

def send_telegram(message):
    """Send Telegram notification"""
    if not ENABLE_TELEGRAM:
        return
    
    # Check if all required telegram settings are configured
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        logging.error("Telegram enabled but missing required configuration (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        logging.info("Telegram notification sent successfully")
    except Exception as e:
        logging.error(f"Telegram notification failed: {e}")

def send_discord(old_ip, new_ip):
    """Send Discord notification"""
    if not ENABLE_DISCORD:
        return
    
    # Check if webhook URL is configured
    if not DISCORD_WEBHOOK_URL:
        logging.error("Discord enabled but missing DISCORD_WEBHOOK_URL")
        return
    
    try:
        # Create embed with IP change information
        embed = {
            "title": "🌐 WAN IP Address Changed",
            "description": f"The WAN IP address for **{SERVER_NAME}** has changed.",
            "color": 3447003,  # Blue color
            "fields": [
                {
                    "name": "Previous IP",
                    "value": f"`{old_ip if old_ip else 'N/A'}`",
                    "inline": True
                },
                {
                    "name": "New IP",
                    "value": f"`{new_ip}`",
                    "inline": True
                },
                {
                    "name": "Server",
                    "value": SERVER_NAME,
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": f"WANwatcher v{VERSION}"
            }
        }
        
        # Payload with embed
        payload = {
            "embeds": [embed],
            "username": "WANwatcher",
            # Using the wan_watcher.png from the GitHub repository
            "avatar_url": "https://raw.githubusercontent.com/noxied/wanwatcher/main/wan_watcher.png"
        }
        
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code in [200, 204]:
            logging.info("Discord notification sent successfully")
        else:
            logging.error(f"Discord notification failed (Status: {response.status_code}): {response.text}")
    
    except Exception as e:
        logging.error(f"Discord notification failed: {e}")

def send_notifications(old_ip, new_ip):
    """Send notifications through all enabled channels"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Email
    if ENABLE_EMAIL:
        subject = f"WAN IP Changed - {SERVER_NAME}"
        body = f"""
WAN IP Address Change Notification

Server: {SERVER_NAME}
Previous IP: {old_ip if old_ip else 'N/A'}
New IP: {new_ip}
Timestamp: {timestamp}

This is an automated notification from WANwatcher.
"""
        send_email(subject, body)
    
    # Telegram
    if ENABLE_TELEGRAM:
        message = f"""
🌐 <b>WAN IP Changed</b>

<b>Server:</b> {SERVER_NAME}
<b>Previous IP:</b> <code>{old_ip if old_ip else 'N/A'}</code>
<b>New IP:</b> <code>{new_ip}</code>
<b>Time:</b> {timestamp}
"""
        send_telegram(message)
    
    # Discord
    if ENABLE_DISCORD:
        send_discord(old_ip, new_ip)

def main():
    """Main monitoring loop"""
    logging.info("=" * 60)
    logging.info(f"WANwatcher v{VERSION} Docker started")
    logging.info(f"Server Name: {SERVER_NAME}")
    logging.info(f"Check Interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL // 60} minutes)")
    
    # Log enabled notification methods with proper configuration checks
    enabled_methods = []
    
    # Check Email configuration
    if ENABLE_EMAIL and all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        enabled_methods.append("Email")
    elif ENABLE_EMAIL:
        logging.warning("Email is enabled but not fully configured (missing SMTP settings)")
    
    # Check Telegram configuration  
    if ENABLE_TELEGRAM and all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        enabled_methods.append("Telegram")
    elif ENABLE_TELEGRAM:
        logging.warning("Telegram is enabled but not fully configured (missing BOT_TOKEN or CHAT_ID)")
    
    # Check Discord configuration
    if ENABLE_DISCORD and DISCORD_WEBHOOK_URL:
        enabled_methods.append("Discord")
    elif ENABLE_DISCORD:
        logging.warning("Discord is enabled but not fully configured (missing WEBHOOK_URL)")
    
    if enabled_methods:
        logging.info(f"Enabled notifications: {', '.join(enabled_methods)}")
    else:
        logging.warning("No notification methods enabled!")
    
    logging.info("=" * 60)
    
    # Initial check
    try:
        current_ip = get_wan_ip()
        last_ip = read_last_ip()
        
        logging.info(f"Current WAN IP: {current_ip}")
        
        if last_ip != current_ip:
            logging.info(f"IP changed from {last_ip} to {current_ip}")
            send_notifications(last_ip, current_ip)
            write_last_ip(current_ip)
        else:
            logging.info("IP unchanged")
    
    except Exception as e:
        logging.error(f"Error during initial check: {e}")
    
    # Continuous monitoring
    logging.info(f"Starting continuous monitoring (checking every {CHECK_INTERVAL} seconds)...")
    
    while True:
        try:
            time.sleep(CHECK_INTERVAL)
            
            current_ip = get_wan_ip()
            last_ip = read_last_ip()
            
            if last_ip != current_ip:
                logging.info(f"IP changed from {last_ip} to {current_ip}")
                send_notifications(last_ip, current_ip)
                write_last_ip(current_ip)
            else:
                logging.info(f"IP check: {current_ip} (unchanged)")
        
        except Exception as e:
            logging.error(f"Error during monitoring: {e}")
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    main()
