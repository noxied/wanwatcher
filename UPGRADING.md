# Upgrading from v1.1.0 to v1.2.0

## 🔄 Upgrade Process

### Step 1: Pull New Image

```bash
# Stop container
docker stop wanwatcher

# Pull new version
docker pull noxied/wanwatcher:1.2.0

# Or pull latest
docker pull noxied/wanwatcher:latest
```

### Step 2: Update Configuration

If you want to add Telegram notifications (new in v1.2.0):

```yaml
environment:
  # Existing Discord config (keep as-is)
  DISCORD_WEBHOOK_URL: "your_webhook_url"
  
  # NEW: Add Telegram configuration
  TELEGRAM_ENABLED: "true"
  TELEGRAM_BOT_TOKEN: "your_bot_token"
  TELEGRAM_CHAT_ID: "your_chat_id"
  TELEGRAM_PARSE_MODE: "HTML"
```

See [README.md](README.md) for how to get Telegram bot token and chat ID.

### Step 3: Restart Container

**Via Docker Compose:**
```bash
docker-compose up -d
```

**Via Portainer:**
1. Edit stack with new environment variables
2. Enable "Pull latest image"
3. Click "Update"

**Via Docker CLI:**
```bash
docker start wanwatcher
```

### Step 4: Trigger Initial Notification (Important!)

After upgrading, you should trigger a notification to test both platforms:

```bash
# Remove old database
docker exec wanwatcher rm /data/ipinfo.db

# Restart container
docker restart wanwatcher

# Check logs
docker logs -f wanwatcher
```

**Why?**
- Ensures v1.2.0 sends initial notifications
- Tests both Discord and Telegram
- Verifies version display is working

You should receive "Initial IP Detection" notifications in:
- Discord (with improved layout)
- Telegram (if configured)

Both will show "Version: v1.2.0"

---

## ✅ Verification

After upgrade, verify:

1. **Check container is running v1.2.0:**
   ```bash
   docker logs wanwatcher | grep "v1.2.0"
   ```

2. **Check notification providers:**
   ```bash
   docker logs wanwatcher | grep "Notification Status" -A 3
   ```
   
   Should show:
   ```
   Notification Status:
     Discord: Configured
     Telegram: Enabled (if configured)
     ipinfo.io: Configured (if configured)
   ```

3. **Check Discord notification:**
   - Should show "Version: v1.2.0" in Environment field
   - Should show "WANwatcher v1.2.0 on [your_server]" in footer
   - Improved spacing between IP fields

4. **Check Telegram notification (if enabled):**
   - Should receive message from your bot
   - Should show "Version: v1.2.0"
   - Clean HTML formatting

---

## 🆕 What's New in v1.2.0

### New Features
- **Telegram Bot Support** - Receive notifications via Telegram
- **Multi-Platform Notifications** - Use Discord, Telegram, or both
- **Version Display** - See which version sent each notification
- **Improved Discord Layout** - Better spacing and readability

### New Environment Variables
```bash
TELEGRAM_ENABLED="false"        # Enable Telegram notifications
TELEGRAM_BOT_TOKEN=""           # Bot token from @BotFather
TELEGRAM_CHAT_ID=""             # Your Telegram chat ID
TELEGRAM_PARSE_MODE="HTML"      # Message format (HTML or Markdown)
```

### Breaking Changes
**None!** - v1.2.0 is fully backward compatible with v1.1.0

If you don't configure Telegram, everything works exactly as before (Discord-only).

---

## 🔧 Troubleshooting

### No Telegram Notifications

1. **Check bot token and chat ID:**
   ```bash
   docker inspect wanwatcher | grep TELEGRAM
   ```

2. **Test Telegram API:**
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"
   ```

3. **Verify you started chat with bot:**
   - Open Telegram
   - Find your bot
   - Send `/start` command

4. **Check logs:**
   ```bash
   docker logs wanwatcher | grep -i telegram
   ```

### Container Shows Old Version

If logs still show old version message:

```bash
# Force remove old image
docker stop wanwatcher
docker rm wanwatcher
docker rmi noxied/wanwatcher:latest

# Pull fresh image
docker pull noxied/wanwatcher:1.2.0

# Recreate container
docker-compose up -d
# or redeploy via Portainer
```

### Database Issues

If you see no notifications after upgrade:

```bash
# Remove database to trigger fresh detection
docker exec wanwatcher rm /data/ipinfo.db
docker restart wanwatcher
```

---

## 📚 Additional Resources

- [README.md](README.md) - Full documentation
- [CHANGELOG.md](CHANGELOG.md) - Complete changelog
- [SECURITY.md](SECURITY.md) - Security best practices
- [GitHub Issues](https://github.com/noxied/wanwatcher/issues) - Report issues

---

## 🎉 Success!

Once you see:
- ✅ "WANwatcher v1.2.0 Docker started" in logs
- ✅ Notifications in Discord (with version)
- ✅ Notifications in Telegram (if enabled)

**You're all set!** WANwatcher will now monitor your IPs and notify both platforms when they change.
