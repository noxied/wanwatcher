#!/bin/bash
# WANwatcher Installation Script
# Automated installation for traditional deployment

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "WANwatcher Installation Script"
echo -e "==========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Detect OS
echo -e "${YELLOW}[1/8] Detecting operating system...${NC}"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    echo -e "${GREEN}✓ Detected: $OS${NC}"
else
    echo -e "${RED}✗ Cannot detect OS${NC}"
    exit 1
fi

# Check Python version
echo ""
echo -e "${YELLOW}[2/8] Checking Python installation...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python $PYTHON_VERSION installed${NC}"
else
    echo -e "${RED}✗ Python 3 not found${NC}"
    echo "Installing Python3..."
    apt-get update && apt-get install -y python3 python3-pip
fi

# Create directories
echo ""
echo -e "${YELLOW}[3/8] Creating directories...${NC}"
mkdir -p /root/wanwatcher
mkdir -p /var/lib/wanwatcher
mkdir -p /var/log
echo -e "${GREEN}✓ Directories created${NC}"

# Copy script
echo ""
echo -e "${YELLOW}[4/8] Installing WANwatcher script...${NC}"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [ -f "$SCRIPT_DIR/wanwatcher.py" ]; then
    cp "$SCRIPT_DIR/wanwatcher.py" /root/wanwatcher/
    chmod +x /root/wanwatcher/wanwatcher.py
    echo -e "${GREEN}✓ Script installed${NC}"
else
    echo -e "${RED}✗ wanwatcher.py not found in script directory${NC}"
    echo "Please ensure wanwatcher.py is in the same directory as this script"
    exit 1
fi

# Install dependencies
echo ""
echo -e "${YELLOW}[5/8] Installing Python dependencies...${NC}"
if command -v pip3 &> /dev/null; then
    pip3 install requests --break-system-packages 2>/dev/null || pip3 install requests
    echo -e "${GREEN}✓ Dependencies installed via pip${NC}"
else
    echo "pip3 not available, using manual installation..."
    bash "$SCRIPT_DIR/install-requests.sh"
fi

# Install ipinfo (optional)
echo ""
echo -e "${YELLOW}[6/8] Installing ipinfo module...${NC}"
read -p "Install ipinfo for geographic data? (y/n): " INSTALL_IPINFO
if [ "$INSTALL_IPINFO" = "y" ]; then
    if [ -f "$SCRIPT_DIR/install-ipinfo.sh" ]; then
        bash "$SCRIPT_DIR/install-ipinfo.sh"
    else
        pip3 install ipinfo --break-system-packages 2>/dev/null || pip3 install ipinfo || true
    fi
    echo -e "${GREEN}✓ ipinfo installed${NC}"
else
    echo "Skipping ipinfo installation"
fi

# Configure
echo ""
echo -e "${YELLOW}[7/8] Configuration...${NC}"
echo "Please configure the script with your Discord webhook:"
echo "  sudo nano /root/wanwatcher/wanwatcher.py"
echo ""
echo "Update these lines:"
echo "  DISCORD_WEBHOOK_URL = \"https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN\""
echo "  SERVER_NAME = \"My Server\""
echo "  IPINFO_TOKEN = \"\"  # Optional"
echo ""
read -p "Press Enter to open editor (or Ctrl+C to configure later)..." _
nano /root/wanwatcher/wanwatcher.py

# Test installation
echo ""
echo -e "${YELLOW}[8/8] Testing installation...${NC}"
echo "Running test..."
python3 /root/wanwatcher/wanwatcher.py
echo ""

# Setup cron
echo ""
echo -e "${YELLOW}Setting up automation...${NC}"
read -p "Would you like to set up automatic monitoring with cron? (y/n): " SETUP_CRON
if [ "$SETUP_CRON" = "y" ]; then
    echo "Select check interval:"
    echo "  1) Every 5 minutes"
    echo "  2) Every 15 minutes (recommended)"
    echo "  3) Every 30 minutes"
    echo "  4) Every hour"
    read -p "Choice [2]: " CRON_CHOICE
    CRON_CHOICE=${CRON_CHOICE:-2}
    
    case $CRON_CHOICE in
        1) CRON_SCHEDULE="*/5 * * * *";;
        2) CRON_SCHEDULE="*/15 * * * *";;
        3) CRON_SCHEDULE="*/30 * * * *";;
        4) CRON_SCHEDULE="0 * * * *";;
        *) CRON_SCHEDULE="*/15 * * * *";;
    esac
    
    # Add to crontab
    CRON_COMMAND="$CRON_SCHEDULE /usr/bin/python3 /root/wanwatcher/wanwatcher.py >> /var/log/wanwatcher-cron.log 2>&1"
    (crontab -l 2>/dev/null | grep -v "wanwatcher"; echo "$CRON_COMMAND") | crontab -
    echo -e "${GREEN}✓ Cron job added${NC}"
    echo "WANwatcher will check every $(echo $CRON_SCHEDULE | cut -d' ' -f1-2)"
fi

# Final instructions
echo ""
echo -e "${GREEN}=========================================="
echo "✓ Installation Complete!"
echo -e "==========================================${NC}"
echo ""
echo -e "${BLUE}What's next:${NC}"
echo ""
echo "1. WANwatcher is installed in: /root/wanwatcher/"
echo "2. IP database will be stored in: /var/lib/wanwatcher/ipinfo.db"
echo "3. Logs are in: /var/log/wanwatcher.log"
echo ""
echo -e "${BLUE}Commands:${NC}"
echo "  Run manually:   python3 /root/wanwatcher/wanwatcher.py"
echo "  View logs:      tail -f /var/log/wanwatcher.log"
echo "  Check IP:       cat /var/lib/wanwatcher/ipinfo.db"
echo "  Edit config:    nano /root/wanwatcher/wanwatcher.py"
echo "  Edit cron:      crontab -e"
echo ""
if [ "$SETUP_CRON" = "y" ]; then
    echo -e "${YELLOW}Automatic monitoring is enabled!${NC}"
    echo "Check Discord for notifications when your IP changes."
else
    echo -e "${YELLOW}Remember to set up cron for automatic monitoring:${NC}"
    echo "  crontab -e"
    echo "  Add: */15 * * * * /usr/bin/python3 /root/wanwatcher/wanwatcher.py >> /var/log/wanwatcher-cron.log 2>&1"
fi
echo ""
echo -e "${GREEN}Happy monitoring! 🚀${NC}"
echo ""
