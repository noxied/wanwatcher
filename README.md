<div align="center">

![WANwatcher Banner](wanwatcher-banner.png)

# WANwatcher

**🌐 Professional WAN IP monitoring with multi-platform notifications**

[![Docker Hub](https://img.shields.io/docker/v/noxied/wanwatcher?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/noxied/wanwatcher)
[![Docker Pulls](https://img.shields.io/docker/pulls/noxied/wanwatcher?logo=docker)](https://hub.docker.com/r/noxied/wanwatcher)
[![GitHub release](https://img.shields.io/github/v/release/noxied/wanwatcher?logo=github)](https://github.com/noxied/wanwatcher/releases)
[![GitHub Stars](https://img.shields.io/github/stars/noxied/wanwatcher?style=social)](https://github.com/noxied/wanwatcher)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Monitor your WAN IPv4 and IPv6 addresses and receive instant notifications via **Discord**, **Telegram**, and **Email** when they change.

Perfect for homelabs, remote access, dynamic DNS monitoring, and more! 🏠

[Features](#features) • [Quick Start](#quick-start) • [Configuration](#configuration) • [Documentation](#documentation) • [Upgrading](UPGRADING.md)

</div>

## ✨ Features

- 🔄 **Automatic IP Change Detection** - Monitors both IPv4 and IPv6
- 📱 **Multi-Platform Notifications** - Discord, Telegram, or Email (or all simultaneously)
- 🎛️ **Explicit Enable/Disable Flags** - Full control over notification platforms
- 🖼️ **Configurable Discord Avatars** - Use webhook's avatar or custom URL
- 🌍 **Geographic Information** - Optional location data via ipinfo.io
- 🐳 **Docker Optimized** - Lightweight, continuous monitoring
- 💾 **Persistent Storage** - Survives container restarts
- 📦 **Multi-Architecture** - Supports AMD64 and ARM64
- ⚡ **Resource Efficient** - ~50-60MB RAM usage
- 🛡️ **Error Handling** - Automatic recovery and error notifications

## 🆕 What's New in v1.3.1

- ✅ **DISCORD_ENABLED Flag** - Explicit control for Discord notifications (consistency with other platforms)
- ✅ **Improved Avatar Handling** - Respects webhook's configured avatar by default
- ✅ **Bug Fixes** - Fixed Discord avatar issues and version display consistency
- ✅ **Better Configuration Validation** - Clear status messages on startup

See [CHANGELOG.md](CHANGELOG.md) for full version history.

## 🚀 Quick Start

### Prerequisites

Choose at least one notification platform:

**Option 1: Discord** (Webhook)
1. Go to Discord Server Settings → Integrations → Webhooks
2. Create New Webhook
3. Configure avatar (optional - in webhook settings)
4. Copy the Webhook URL

**Option 2: Telegram** (Bot)
1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the instructions
3. Save your bot token (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Message [@userinfobot](https://t.me/userinfobot) to get your Chat ID
5. Start a chat with your new bot (send `/start`)

**Option 3: Email** (SMTP)
1. Configure your SMTP server details
2. Enable "less secure apps" or use app-specific password if required

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
   ```yaml
   environment:
     # Discord Configuration
     DISCORD_ENABLED: "true"                    # NEW in v1.3.1 - Must be "true" to enable
     DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/..."
     DISCORD_AVATAR_URL: ""                     # Optional custom avatar URL
     
     # Telegram Configuration
     TELEGRAM_ENABLED: "false"                  # Set to "true" to enable
     TELEGRAM_BOT_TOKEN: ""
     TELEGRAM_CHAT_ID: ""
     
     # Email Configuration
     EMAIL_ENABLED: "false"                     # Set to "true" to enable
     EMAIL_SMTP_HOST: ""
     EMAIL_SMTP_PORT: "587"
     
     # General Settings
     SERVER_NAME: "My Server"
     CHECK_INTERVAL: "900"
   ```

3. **Start the container:**
   ```bash
   docker-compose up -d
   ```

4. **Check logs:**
   ```bash
   docker-compose logs -f
   ```
   
   You should see:
   ```
   Notification Status:
     Discord: Configured ✓
     Telegram: Not enabled
     Email: Not enabled
   ```

### Using Docker Run

**Discord notifications:**
```bash
docker run -d \
  --name wanwatcher \
  --restart unless-stopped \
  -e DISCORD_ENABLED="true" \
  -e DISCORD_WEBHOOK_URL="your_discord_webhook_url" \
  -e SERVER_NAME="My Server" \
  -e CHECK_INTERVAL="900" \
  -v $(pwd)/data:/data \
  -v $(pwd)/logs:/logs \
  noxied/wanwatcher:latest
```

**For Telegram, add:**
```bash
  -e TELEGRAM_ENABLED="true" \
  -e TELEGRAM_BOT_TOKEN="your_telegram_bot_token" \
  -e TELEGRAM_CHAT_ID="your_telegram_chat_id" \
```

**For Email, add:**
```bash
  -e EMAIL_ENABLED="true" \
  -e EMAIL_SMTP_HOST="smtp.gmail.com" \
  -e EMAIL_SMTP_PORT="587" \
  -e EMAIL_SMTP_USER="your_email@gmail.com" \
  -e EMAIL_SMTP_PASSWORD="your_app_password" \
  -e EMAIL_FROM="your_email@gmail.com" \
  -e EMAIL_TO="recipient@example.com" \
```

## 📚 Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes
- **[UPGRADING.md](UPGRADING.md)** - How to upgrade between versions
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

## Upgrading
   
See [UPGRADING.md](UPGRADING.md) for detailed instructions on upgrading from previous versions.

**⚠️ Important for v1.3.0 users:** v1.3.1 requires adding `DISCORD_ENABLED="true"` to enable Discord notifications.

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| **Discord Settings** | | | |
| `DISCORD_ENABLED` | No | `false` | Enable/disable Discord notifications (NEW in v1.3.1) |
| `DISCORD_WEBHOOK_URL` | No* | - | Discord webhook URL for notifications |
| `DISCORD_AVATAR_URL` | No | - | Custom avatar URL (optional, uses webhook's avatar by default) |
| **Telegram Settings** | | | |
| `TELEGRAM_ENABLED` | No | `false` | Enable Telegram notifications |
| `TELEGRAM_BOT_TOKEN` | No* | - | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | No* | - | Your Telegram chat ID |
| `TELEGRAM_PARSE_MODE` | No | `HTML` | Message format: `HTML` or `Markdown` |
| **Email Settings** | | | |
| `EMAIL_ENABLED` | No | `false` | Enable email notifications |
| `EMAIL_SMTP_HOST` | No* | - | SMTP server address (e.g., smtp.gmail.com) |
| `EMAIL_SMTP_PORT` | No | `587` | SMTP server port |
| `EMAIL_USE_TLS` | No | `true` | Use TLS encryption |
| `EMAIL_SMTP_USER` | No* | - | SMTP username |
| `EMAIL_SMTP_PASSWORD` | No* | - | SMTP password or app-specific password |
| `EMAIL_FROM` | No* | - | Sender email address |
| `EMAIL_TO` | No* | - | Recipient email address |
| **General Settings** | | | |
| `SERVER_NAME` | No | `WANwatcher Docker` | Server name for identification |
| `BOT_NAME` | No | `WANwatcher` | Bot display name |
| `CHECK_INTERVAL` | No | `900` | Check interval in seconds (15 min) |
| `IPINFO_TOKEN` | No | - | ipinfo.io token for geographic data |
| `MONITOR_IPV4` | No | `true` | Enable IPv4 monitoring |
| `MONITOR_IPV6` | No | `true` | Enable IPv6 monitoring |

\* Required only if the corresponding platform is enabled. At least one notification platform must be enabled.

### Notification Platform Options

**1. Discord Only:**
```yaml
environment:
  DISCORD_ENABLED: "true"
  DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/..."
  TELEGRAM_ENABLED: "false"
  EMAIL_ENABLED: "false"
```

**2. Telegram Only:**
```yaml
environment:
  DISCORD_ENABLED: "false"
  TELEGRAM_ENABLED: "true"
  TELEGRAM_BOT_TOKEN: "123456789:ABC..."
  TELEGRAM_CHAT_ID: "123456789"
  EMAIL_ENABLED: "false"
```

**3. Email Only:**
```yaml
environment:
  DISCORD_ENABLED: "false"
  TELEGRAM_ENABLED: "false"
  EMAIL_ENABLED: "true"
  EMAIL_SMTP_HOST: "smtp.gmail.com"
  EMAIL_SMTP_USER: "your_email@gmail.com"
  EMAIL_SMTP_PASSWORD: "your_app_password"
  EMAIL_FROM: "your_email@gmail.com"
  EMAIL_TO: "recipient@example.com"
```

**4. All Platforms (Recommended for redundancy):**
```yaml
environment:
  DISCORD_ENABLED: "true"
  DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/..."
  TELEGRAM_ENABLED: "true"
  TELEGRAM_BOT_TOKEN: "123456789:ABC..."
  TELEGRAM_CHAT_ID: "123456789"
  EMAIL_ENABLED: "true"
  EMAIL_SMTP_HOST: "smtp.gmail.com"
  EMAIL_SMTP_USER: "your_email@gmail.com"
  EMAIL_SMTP_PASSWORD: "your_app_password"
  EMAIL_FROM: "your_email@gmail.com"
  EMAIL_TO: "recipient@example.com"
```

### Configuration Validation

WANwatcher validates your configuration on startup. Check logs for:

```
Notification Status:
  Discord: Configured ✓
  Telegram: Not enabled
  Email: Configured ✓
```

If you see errors, verify:
1. Platform `*_ENABLED` flags are set to `"true"` (with quotes)
2. All required credentials are provided for enabled platforms
3. URLs and tokens are valid and not expired

### Enabling Discord Notifications

To enable Discord notifications:

1. Set `DISCORD_ENABLED="true"`
2. Provide your `DISCORD_WEBHOOK_URL`
3. (Optional) Configure avatar (see below)

**Example:**
```yaml
environment:
  DISCORD_ENABLED: "true"
  DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
```

### Discord Avatar Configuration

**Option 1: Use Webhook's Avatar (Recommended)**
1. Go to Discord Server Settings > Integrations > Webhooks
2. Edit your webhook
3. Set an avatar image
4. Leave `DISCORD_AVATAR_URL` empty in your config
5. WANwatcher will use the webhook's avatar automatically

**Option 2: Use Custom Avatar URL**
```yaml
environment:
  DISCORD_AVATAR_URL: "https://example.com/your-avatar.png"
```

**Custom avatar requirements:**
- Must be publicly accessible URL
- Must use `http://` or `https://` scheme
- Must be a valid image file (PNG, JPG, GIF)
- Must be under 2048 characters

**Note:** Discord will use your webhook's configured avatar by default if `DISCORD_AVATAR_URL` is not provided. This is the recommended approach as it's simpler and more reliable.

## 📧 Email Setup

### Gmail Configuration

1. **Enable 2-Factor Authentication** (if not already enabled)
2. **Generate App Password:**
   - Go to [Google Account Settings](https://myaccount.google.com/security)
   - Click on "2-Step Verification"
   - Scroll to "App passwords"
   - Generate a new app password for "Mail"
   
3. **Configure WANwatcher:**
   ```yaml
   EMAIL_ENABLED: "true"
   EMAIL_SMTP_HOST: "smtp.gmail.com"
   EMAIL_SMTP_PORT: "587"
   EMAIL_SMTP_USER: "your_email@gmail.com"
   EMAIL_SMTP_PASSWORD: "your_16_char_app_password"
   EMAIL_FROM: "your_email@gmail.com"
   EMAIL_TO: "recipient@example.com"
   ```

### Other Email Providers

**Outlook/Hotmail:**
```yaml
EMAIL_SMTP_HOST: "smtp-mail.outlook.com"
EMAIL_SMTP_PORT: "587"
```

**Yahoo Mail:**
```yaml
EMAIL_SMTP_HOST: "smtp.mail.yahoo.com"
EMAIL_SMTP_PORT: "587"
```

**Custom SMTP:**
```yaml
EMAIL_SMTP_HOST: "mail.example.com"
EMAIL_SMTP_PORT: "587"
EMAIL_USE_TLS: "true"
```

## 📱 Telegram Setup

### Creating a Telegram Bot

1. **Create the bot:**
   ```
   Open Telegram → Search for @BotFather
   Send: /newbot
   Follow the instructions
   Save your bot token
   ```

2. **Get your Chat ID:**
   ```
   Search for @userinfobot
   Send: /start
   Copy your Chat ID
   ```

3. **Start your bot:**
   ```
   Search for your bot
   Send: /start
   ```

4. **Configure WANwatcher:**
   ```yaml
   TELEGRAM_ENABLED: "true"
   TELEGRAM_BOT_TOKEN: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
   TELEGRAM_CHAT_ID: "123456789"
   ```

## 📦 Volume Mounts

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

## 📊 Monitoring

### View Logs

```bash
# Real-time logs
docker logs -f wanwatcher

# Last 50 lines
docker logs --tail 50 wanwatcher

# With docker-compose
docker-compose logs -f wanwatcher
```

### Check Status

```bash
# Container status
docker ps | grep wanwatcher

# Resource usage
docker stats wanwatcher

# With docker-compose
docker-compose ps
```

## 🧪 Testing

### Force Notification

```bash
# Remove database to trigger first-run notification
docker exec wanwatcher rm /data/ipinfo.db
docker restart wanwatcher

# With docker-compose
docker-compose exec wanwatcher rm /data/ipinfo.db
docker-compose restart wanwatcher
```

## 🔧 Troubleshooting

### No Notifications Received

1. **Check logs for configuration validation:**
   ```bash
   docker logs wanwatcher | grep "Notification Status"
   ```

2. **Verify platform is enabled:**
   ```bash
   docker exec wanwatcher env | grep DISCORD_ENABLED
   # Should show: DISCORD_ENABLED=true
   ```

3. **Test Discord webhook:**
   ```bash
   curl -X POST -H "Content-Type: application/json" \
     -d '{"content":"Test"}' "YOUR_DISCORD_WEBHOOK_URL"
   ```

4. **Test Telegram bot:**
   ```bash
   curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getMe"
   ```

### Discord Notifications Not Working (v1.3.1)

If you upgraded from v1.3.0 or earlier and notifications stopped:

1. **Check if DISCORD_ENABLED is set:**
   ```bash
   docker logs wanwatcher | grep "Discord"
   ```

2. **Add the required flag:**
   ```yaml
   environment:
     DISCORD_ENABLED: "true"  # Required in v1.3.1+
     DISCORD_WEBHOOK_URL: "https://..."
   ```

3. **Restart container:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

See [UPGRADING.md](UPGRADING.md) for more details on v1.3.1 changes.

### Avatar Not Displaying

**Option 1 (Recommended):** Configure in Discord
1. Go to Discord Server Settings > Integrations > Webhooks
2. Edit webhook and set avatar
3. Leave `DISCORD_AVATAR_URL` empty

**Option 2:** Use custom URL
```yaml
DISCORD_AVATAR_URL: "https://example.com/avatar.png"
```

For more troubleshooting, see [docs/troubleshooting.md](docs/troubleshooting.md)

## 🔒 Security Best Practices

1. **Never commit secrets to version control**
   - Use environment variables
   - Add `.env` to `.gitignore`

2. **Keep tokens private**
   - Webhook URLs and bot tokens are sensitive
   - Rotate tokens periodically

3. **Use app-specific passwords**
   - For email, use app passwords instead of main password
   - Enable 2FA on your email account

## 📊 Performance

- **Memory:** ~50-60MB
- **CPU:** <1% idle, ~2-5% during checks
- **Disk:** <100MB (image + logs)
- **Network:** Minimal (only during IP checks and notifications)

## 🤝 Contributing

Contributions are welcome! Please submit a Pull Request.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔧 Support

- **Issues:** [GitHub Issues](https://github.com/noxied/wanwatcher/issues)
- **Discussions:** [GitHub Discussions](https://github.com/noxied/wanwatcher/discussions)
- **Documentation:** [CHANGELOG.md](CHANGELOG.md) | [UPGRADING.md](UPGRADING.md)

## 📜 Changelog

See [CHANGELOG.md](CHANGELOG.md) for complete version history.

---

**Made with ❤️ for homelab enthusiasts**
