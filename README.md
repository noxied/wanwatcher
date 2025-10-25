![WANwatcher Banner](https://raw.githubusercontent.com/noxied/wanwatcher/main/wanwatcher-banner.png)

# WANwatcher - WAN IP Monitoring with Discord Notifications

Monitor your WAN IP address (IPv4 and IPv6) and receive beautiful Discord notifications when it changes. Perfect for home labs, dynamic IPs, and remote servers.

[![Docker Pulls](https://img.shields.io/docker/pulls/noxied/wanwatcher)](https://hub.docker.com/r/noxied/wanwatcher)
[![Docker Image Size](https://img.shields.io/docker/image-size/noxied/wanwatcher/latest)](https://hub.docker.com/r/noxied/wanwatcher)
[![GitHub release](https://img.shields.io/github/v/release/noxied/wanwatcher)](https://github.com/noxied/wanwatcher/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Quick Start

```bash
docker run -d \
  --name wanwatcher \
  --restart unless-stopped \
  -e DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN" \
  -e SERVER_NAME="My Server" \
  -v $(pwd)/data:/data \
  -v $(pwd)/logs:/logs \
  noxied/wanwatcher:latest
```

## ✨ Features

- 🌐 **IPv4 & IPv6 Support** - Monitor both protocols simultaneously
- 🔔 **Instant Discord Notifications** - Know immediately when your IP changes
- 🌍 **Geographic Details** - Optional city, country, ISP, and timezone info
- 🛡️ **Reliable** - Multiple fallback IP detection services
- ⚡ **Lightweight** - Only ~50-60MB RAM usage
- 🔄 **Continuous Monitoring** - Built-in loop, no cron needed
- 🏗️ **Multi-Architecture** - Native support for AMD64 and ARM64
- 📝 **Well Logged** - Complete activity tracking

## 🐳 Docker Compose (Recommended)

```yaml
version: '3.8'

services:
  wanwatcher:
    image: noxied/wanwatcher:latest
    container_name: wanwatcher
    restart: unless-stopped
    
    environment:
      # Required
      DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN"
      
      # Optional Configuration
      IPINFO_TOKEN: ""              # Get free token at ipinfo.io/signup
      SERVER_NAME: "My Server"      # Server identification
      CHECK_INTERVAL: "900"         # Check every 15 minutes (in seconds)
      BOT_NAME: "WANwatcher"        # Discord bot name
      
      # IPv6 Configuration (NEW in v1.1.0)
      MONITOR_IPV4: "true"          # Monitor IPv4 addresses (default: true)
      MONITOR_IPV6: "true"          # Monitor IPv6 addresses (default: true)
    
    volumes:
      - ./data:/data                # Persist IP database
      - ./logs:/logs                # Persist logs
```

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_WEBHOOK_URL` | **Yes** | - | Your Discord webhook URL |
| `IPINFO_TOKEN` | No | `""` | ipinfo.io API token for geo data |
| `SERVER_NAME` | No | `"My Server"` | Server identifier in notifications |
| `CHECK_INTERVAL` | No | `900` | Check interval in seconds (900 = 15 min) |
| `BOT_NAME` | No | `"WANwatcher"` | Discord bot username |
| `MONITOR_IPV4` | No | `true` | Enable IPv4 monitoring |
| `MONITOR_IPV6` | No | `true` | Enable IPv6 monitoring |

### Check Interval Examples

```yaml
CHECK_INTERVAL: "300"   # Every 5 minutes
CHECK_INTERVAL: "900"   # Every 15 minutes (recommended)
CHECK_INTERVAL: "1800"  # Every 30 minutes
CHECK_INTERVAL: "3600"  # Every hour
CHECK_INTERVAL: "21600" # Every 6 hours
```

### IPv6 Configuration

WANwatcher can monitor IPv4 only, IPv6 only, or both simultaneously:

```yaml
# Monitor both (default)
MONITOR_IPV4: "true"
MONITOR_IPV6: "true"

# IPv4 only
MONITOR_IPV4: "true"
MONITOR_IPV6: "false"

# IPv6 only
MONITOR_IPV4: "false"
MONITOR_IPV6: "true"
```

## 📋 Setup Discord Webhook

1. Open Discord → Server Settings → Integrations → Webhooks
2. Click "Create Webhook"
3. Name it (e.g., "WANwatcher")
4. Select channel for notifications
5. Copy webhook URL
6. Use in `DISCORD_WEBHOOK_URL` environment variable

## 🎨 Notification Examples

### IP Change Notification
```
🌐 WAN IP Monitor Alert
🔄 IP Address Changed
WAN IP for My Server has been updated

📍 Current IPv4: 98.76.54.32
📌 Previous IPv4: 123.45.67.89

📍 Current IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7334
📌 Previous IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7335

📍 Location Information
🌍 Los Angeles, CA, United States
🏢 Example Internet Provider
🕐 America/Los_Angeles

⏰ Detected At: Saturday, October 25, 2025 3:15 AM
🐳 Environment: Running in Docker
```

### First Run Notification
```
🌐 WAN IP Monitor Alert
✅ Initial IP Detection
WAN IP monitoring started for My Server

📍 Current IPv4: 98.76.54.32
📍 Current IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7334
ℹ️ IPv6 Status: Available and monitored

⏰ Detected At: Saturday, October 25, 2025 3:15 AM
🐳 Environment: Running in Docker
```

## 🎮 Management Commands

```bash
# View logs in real-time
docker logs -f wanwatcher

# Check container status
docker ps | grep wanwatcher

# View current IP database
cat data/ipinfo.db

# Restart container
docker restart wanwatcher

# Stop container
docker stop wanwatcher

# Remove container
docker rm wanwatcher

# Update to latest version
docker pull noxied/wanwatcher:latest
docker stop wanwatcher
docker rm wanwatcher
# Then run with your original docker-compose.yml or docker run command
```

## 🖥️ Platform Support

### Architectures
- ✅ **AMD64 (x86_64)** - Desktop, servers, most systems
- ✅ **ARM64 (aarch64)** - Raspberry Pi 4, modern ARM servers
- ✅ **ARM (armhf)** - Older Raspberry Pi models (via ARM64 image)

### Operating Systems
- ✅ Linux (any distribution)
- ✅ Windows (Docker Desktop)
- ✅ macOS (Docker Desktop)

### NAS & Home Server Platforms
- ✅ TrueNAS Scale
- ✅ Synology NAS (DSM 7.0+)
- ✅ QNAP NAS
- ✅ Unraid
- ✅ Proxmox VE
- ✅ Home Assistant OS

### Single Board Computers
- ✅ Raspberry Pi 4/5 (ARM64)
- ✅ Raspberry Pi 3 (ARM64)
- ✅ Raspberry Pi Zero 2 W
- ✅ Other ARM64 SBCs

## 🔧 Troubleshooting

### Container exits immediately
```bash
# Check logs
docker logs wanwatcher

# Verify webhook is configured
docker inspect wanwatcher | grep DISCORD_WEBHOOK_URL
```

### No notifications received
```bash
# Test webhook manually
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"content":"Test message from WANwatcher setup"}' \
  "YOUR_WEBHOOK_URL"

# Check network connectivity
docker exec wanwatcher ping -c 4 8.8.8.8
```

### IPv6 not detected
```bash
# Check if your network supports IPv6
docker exec wanwatcher curl -6 https://api6.ipify.org

# Verify IPv6 is enabled
docker inspect wanwatcher | grep MONITOR_IPV6

# Check logs for IPv6 detection attempts
docker logs wanwatcher | grep -i ipv6
```

### Wrong architecture image
Docker should automatically pull the correct architecture, but you can verify:
```bash
# Check current image architecture
docker image inspect noxied/wanwatcher:latest | grep Architecture

# Force pull specific architecture (if needed)
docker pull --platform linux/amd64 noxied/wanwatcher:latest
docker pull --platform linux/arm64 noxied/wanwatcher:latest
```

## 📊 Resource Usage

- **Memory:** ~50-60MB typical (limit: 128MB)
- **CPU:** <1% typical
- **Disk:** ~100MB (image + logs + data)
- **Network:** Minimal (only during IP checks)

## 🌐 Optional Geographic Data

Get a free API token at [ipinfo.io/signup](https://ipinfo.io/signup) (50,000 requests/month free tier)

```yaml
environment:
  IPINFO_TOKEN: "your_token_here"
```

With geographic data enabled, you'll receive:
- 🌍 City, Region, Country
- 🏢 ISP/Organization name
- 🕐 Timezone information

## 🏷️ Docker Image Tags

| Tag | Description | Architectures |
|-----|-------------|---------------|
| `latest` | Latest stable release | AMD64, ARM64 |
| `1` | Version 1.x (latest) | AMD64, ARM64 |
| `1.1` | Version 1.1.x (latest) | AMD64, ARM64 |
| `1.1.0` | Specific version 1.1.0 | AMD64, ARM64 |
| `1.0` | Version 1.0.x | AMD64, ARM64 |
| `1.0.0` | Specific version 1.0.0 | AMD64, ARM64 |

Pull commands:
```bash
docker pull noxied/wanwatcher:latest
docker pull noxied/wanwatcher:1.1.0
docker pull noxied/wanwatcher:1
```

## 🆕 What's New in v1.1.0

### IPv6 Support
- Monitor both IPv4 and IPv6 addresses simultaneously
- Separate fields in Discord notifications for each protocol
- Configurable monitoring (enable/disable IPv4 or IPv6)
- Multiple fallback services for reliable IPv6 detection

### Multi-Architecture Docker
- Native support for AMD64 (x86_64) - Unraid, most servers
- Native support for ARM64 (aarch64) - Raspberry Pi 4, modern ARM
- Single `docker pull` command works on all platforms!

### Enhanced Notifications
- Beautiful Discord embeds showing both IPv4 and IPv6
- Indicates which protocol changed
- Shows "Not available" for unsupported protocols
- Improved visual layout with emoji indicators

## 📚 Full Documentation

**GitHub Repository:** https://github.com/noxied/wanwatcher

Additional documentation:
- Traditional installation guide (non-Docker)
- Platform-specific setup guides
- Advanced configuration options
- Development and contributing guidelines
- Troubleshooting extended guide

## 🤝 Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/noxied/wanwatcher/issues)
- **Discussions:** [GitHub Discussions](https://github.com/noxied/wanwatcher/discussions)
- **Source Code:** [GitHub Repository](https://github.com/noxied/wanwatcher)
- **Docker Hub:** [noxied/wanwatcher](https://hub.docker.com/r/noxied/wanwatcher)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to all the IP detection services that make this possible
- Built with Python and the Discord Webhook API
- Inspired by the selfhosting community

---

**Made with ❤️ for the selfhosting community**

If you find WANwatcher useful, consider giving it a ⭐ on GitHub!
