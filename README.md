# WANwatcher 🌐

Monitor your WAN IPv4 and IPv6 addresses with real-time notifications to Discord and Telegram when they change.

[![Docker Image](https://img.shields.io/badge/docker-noxied%2Fwanwatcher-blue)](https://hub.docker.com/r/noxied/wanwatcher)
[![Version](https://img.shields.io/badge/version-1.2.0-green)](https://github.com/noxied/wanwatcher/releases/tag/v1.2.0)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

## ✨ Features

- 🔄 **Automatic IP Change Detection** - Monitors both IPv4 and IPv6
- 📱 **Multi-Platform Notifications** - Discord, Telegram, or both simultaneously  
- 🌍 **Geographic Information** - Optional location data via ipinfo.io
- 🐳 **Docker Optimized** - Lightweight, continuous monitoring
- 💾 **Persistent Storage** - Survives container restarts
- 🔁 **Multi-Architecture** - Supports AMD64 and ARM64
- ⚡ **Resource Efficient** - ~50-60MB RAM usage
- 🛡️ **Error Handling** - Automatic recovery and error notifications

## 🆕 What's New in v1.2.0

- ✅ **Telegram Bot Support** - Receive notifications via Telegram
- ✅ **Multi-Platform Notifications** - Use Discord, Telegram, or both
- ✅ **Improved Discord Layout** - Better spacing and readability
- ✅ **Version Display** - See which version sent each notification
- ✅ **Notification Provider Architecture** - Easy to add more platforms

## 🚀 Quick Start

### Prerequisites

Choose at least one notification platform:

**Option 1: Discord** (Webhook)
1. Go to Discord Server Settings → Integrations → Webhooks
2. Create New Webhook
3. Copy the Webhook URL

**Option 2: Telegram** (Bot)
1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the instructions
3. Save your bot token (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Message [@userinfobot](https://t.me/userinfobot) to get your Chat ID
5. Start a chat with your new bot (send `/start`)

**Optional:** Get free ipinfo.io token from [ipinfo.io/signup](https://ipinfo.io/signup)

### Using Docker Compose (Recommended)

1. **Download docker-compose.yml:**
   ```bash
   curl -O https://raw.githubusercontent.com/noxied/wanwatcher/main/docker-compose.yml
   ```

2. **Edit configuration:**
   ```bash
   nano docker-compose.yml
   ```
   
   Configure your notification settings:
   - Set `DISCORD_WEBHOOK_URL` (for Discord)
   - Set `TELEGRAM_ENABLED="true"` and configure bot token/chat ID (for Telegram)
   - Customize `SERVER_NAME`, `CHECK_INTERVAL`, etc.

3. **Start the container:**
   ```bash
   docker-compose up -d
   ```

4. **Check logs:**
   ```bash
   docker-compose logs -f
   ```

### Using Docker Run

```bash
docker run -d \
  --name wanwatcher \
  --restart unless-stopped \
  -e DISCORD_WEBHOOK_URL="your_discord_webhook_url" \
  -e SERVER_NAME="My Server" \
  -e CHECK_INTERVAL="900" \
  -v $(pwd)/data:/data \
  -v $(pwd)/logs:/logs \
  noxied/wanwatcher:latest
```

For Telegram, add:
```bash
  -e TELEGRAM_ENABLED="true" \
  -e TELEGRAM_BOT_TOKEN="your_telegram_bot_token" \
  -e TELEGRAM_CHAT_ID="your_telegram_chat_id" \
```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_WEBHOOK_URL` | No* | - | Discord webhook URL for notifications |
| `TELEGRAM_ENABLED` | No | `false` | Enable Telegram notifications |
| `TELEGRAM_BOT_TOKEN` | No* | - | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | No* | - | Your Telegram chat ID |
| `TELEGRAM_PARSE_MODE` | No | `HTML` | Message format: `HTML` or `Markdown` |
| `SERVER_NAME` | No | `WANwatcher Docker` | Server name for identification |
| `BOT_NAME` | No | `WANwatcher` | Bot display name |
| `CHECK_INTERVAL` | No | `900` | Check interval in seconds (15 min) |
| `IPINFO_TOKEN` | No | - | ipinfo.io token for geographic data |
| `MONITOR_IPV4` | No | `true` | Enable IPv4 monitoring |
| `MONITOR_IPV6` | No | `true` | Enable IPv6 monitoring |

\* At least one notification platform (Discord OR Telegram) must be configured.

### Notification Platform Options

**1. Discord Only:**
```yaml
DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/..."
TELEGRAM_ENABLED: "false"
```

**2. Telegram Only:**
```yaml
DISCORD_WEBHOOK_URL: ""
TELEGRAM_ENABLED: "true"
TELEGRAM_BOT_TOKEN: "123456789:ABC..."
TELEGRAM_CHAT_ID: "123456789"
```

**3. Both Platforms (Recommended):**
```yaml
DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/..."
TELEGRAM_ENABLED: "true"
TELEGRAM_BOT_TOKEN: "123456789:ABC..."
TELEGRAM_CHAT_ID: "123456789"
```

## 📁 Volume Mounts

| Path | Purpose |
|------|---------|
| `/data` | IP database storage (survives restarts) |
| `/logs` | Log file storage |

Example:
```yaml
volumes:
  - ./data:/data      # Database persists here
  - ./logs:/logs      # Logs stored here
```

## 🔍 Monitoring

### View Logs

```bash
# Real-time logs
docker logs -f wanwatcher

# Last 50 lines
docker logs --tail 50 wanwatcher
```

### Check Status

```bash
# Container status
docker ps | grep wanwatcher

# Resource usage
docker stats wanwatcher
```

## 🧪 Testing

### Force Notification

```bash
# Remove database to trigger first-run notification
docker exec wanwatcher rm /data/ipinfo.db
docker restart wanwatcher
```

## 🔧 Troubleshooting

### No Notifications Received

1. **Check logs:**
   ```bash
   docker logs wanwatcher | grep -i error
   ```

2. **Test Discord webhook:**
   ```bash
   curl -X POST -H "Content-Type: application/json" \
     -d '{"content":"Test"}' "YOUR_DISCORD_WEBHOOK_URL"
   ```

3. **Test Telegram bot:**
   ```bash
   curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getMe"
   ```

## 🔐 Security Best Practices

1. **Never commit secrets to version control**
   - Use environment variables
   - Add `.env` to `.gitignore`

2. **Keep tokens private**
   - Webhook URLs and bot tokens are sensitive
   - Rotate tokens periodically

## 📊 Performance

- **Memory:** ~50-60MB
- **CPU:** <1% idle, ~2-5% during checks
- **Disk:** <100MB (image + logs)

## 🤝 Contributing

Contributions are welcome! Please submit a Pull Request.

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 📧 Support

- **Issues:** [GitHub Issues](https://github.com/noxied/wanwatcher/issues)
- **Discussions:** [GitHub Discussions](https://github.com/noxied/wanwatcher/discussions)

## 📜 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Made with ❤️ for homelab enthusiasts**
