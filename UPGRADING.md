# WANwatcher Upgrading Guide

This guide provides detailed instructions for upgrading WANwatcher between versions.

---

## 📋 Quick Upgrade (Any Version)

### For Docker Users:

```bash
# 1. Pull latest image
docker pull noxied/wanwatcher:latest

# 2. Stop current container
docker stop wanwatcher
docker rm wanwatcher

# 3. Start with updated configuration (see version-specific notes below)
docker-compose up -d

# Or if using docker run:
docker run -d --name wanwatcher \
## 🆕 Upgrading to v1.3.2 (from v1.3.1)

**Release Date:** October 29, 2025  
**Type:** Patch/Documentation Fix Release  
**Breaking Changes:** None  
**Downtime:** ~1 minute

### What's New
- **Fixed email template:** Gmail-compatible inline styles for dark theme
- Fixed email variable names in README.md
- Fixed hardcoded version strings in notifications
- Updated wanwatcher.py for consistency
- Email notifications now display professional dark theme

### Required Changes

#### 1. Update Email Variable Names (If Using Email)

If you configured email using README.md examples from v1.3.1, **you must update your variable names**:

**In your `docker-compose.yml` or Docker run command:**

**WRONG (from old README):**
```yaml
environment:
  EMAIL_SMTP_SERVER: "smtp.gmail.com"     # ❌ WRONG - doesn't work!
  EMAIL_USERNAME: "user@gmail.com"        # ❌ WRONG - doesn't work!
  EMAIL_PASSWORD: "your_password"         # ❌ WRONG - doesn't work!
```

**CORRECT (use these):**
```yaml
environment:
  EMAIL_SMTP_HOST: "smtp.gmail.com"       # ✅ CORRECT
  EMAIL_SMTP_USER: "user@gmail.com"       # ✅ CORRECT
  EMAIL_SMTP_PASSWORD: "your_password"    # ✅ CORRECT
```

**Why:** The README had wrong variable names. The Docker code always expected the correct names (EMAIL_SMTP_HOST, EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD).

### Step-by-Step Upgrade

```bash
# 1. Pull new image
docker-compose pull

# Or for specific version:
docker pull noxied/wanwatcher:1.3.2

# 2. If using email, edit docker-compose.yml
nano docker-compose.yml

# Change these lines (if present):
#   EMAIL_SMTP_SERVER → EMAIL_SMTP_HOST
#   EMAIL_USERNAME → EMAIL_SMTP_USER  
#   EMAIL_PASSWORD → EMAIL_SMTP_PASSWORD

# 3. Restart container
docker-compose down
docker-compose up -d

# 4. Verify in logs
docker-compose logs -f wanwatcher

# Look for:
# "WANwatcher v1.3.2 Docker started"
# "Email: Configured ✓" (if using email)
# Notifications now show "v1.3.2"
```

### Verification

After upgrading, check:
- ✅ Version shows as "WANwatcher v1.3.2" in logs
- ✅ Email shows "Configured ✓" (if enabled)
- ✅ Notifications display "v1.3.2" in all platforms
- ✅ Email notifications show dark theme (if enabled)
- ✅ No errors in logs

### Troubleshooting v1.3.2

**Problem:** Email still not working after variable name fix

**Solution:**
1. Verify all variable names are correct (EMAIL_SMTP_HOST, not EMAIL_SMTP_SERVER)
2. Check logs: `docker logs wanwatcher | grep -i email`
3. See TROUBLESHOOTING.md email section for detailed help

**Problem:** Notifications still show "v1.3.1"

**Solution:**
1. Verify image version: `docker inspect wanwatcher | grep "Image"`
2. Should show `noxied/wanwatcher:1.3.2`
3. If not, pull and restart: `docker-compose pull && docker-compose up -d`

---

  --restart unless-stopped \
  -v ./data:/data \
  -v ./logs:/logs \
  -e DISCORD_ENABLED="true" \
  -e DISCORD_WEBHOOK_URL="your_webhook" \
  noxied/wanwatcher:latest
```

---

## 🆕 Upgrading to v1.3.1 (from v1.3.0)

**Release Date:** October 28, 2025  
**Type:** Patch/Bugfix Release  
**Breaking Changes:** None  
**Downtime:** ~1 minute

### What's New
- Fixed Discord notification avatar handling
- Fixed version display consistency
- Added `DISCORD_ENABLED` configuration flag

### Required Changes

#### 1. Add DISCORD_ENABLED Variable

**In your `docker-compose.yml` or Docker run command:**

```yaml
environment:
  DISCORD_ENABLED: "true"  # NEW - Required if using Discord
  DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/..."
```

**Why:** Provides explicit control over Discord notifications, matching the pattern used for Telegram and Email.

#### 2. Optional: Remove DISCORD_AVATAR_URL

If you had set a custom avatar URL and want to use your webhook's configured avatar instead:

```yaml
environment:
  # DISCORD_AVATAR_URL: ""  # Can be removed or left empty
```

### Step-by-Step Upgrade

```bash
# 1. Edit your docker-compose.yml
nano docker-compose.yml

# Add this line under environment:
#   DISCORD_ENABLED: "true"

# 2. Pull new image
docker-compose pull

# 3. Restart container
docker-compose down
docker-compose up -d

# 4. Verify in logs
docker-compose logs -f wanwatcher

# Look for:
# "Discord: Configured ✓"
# "Discord notification sent successfully"
```

### Verification

After upgrading, check:
- ✅ Discord notification arrives with avatar
- ✅ Version shows as "v1.3.1" everywhere
- ✅ No errors in logs

### Troubleshooting v1.3.1

**Problem:** Discord notifications not working after upgrade

**Solution:**
1. Ensure `DISCORD_ENABLED="true"` is set
2. Verify webhook URL is still valid
3. Check logs for specific error messages

**Problem:** Avatar not displaying

**Solution:**
1. Check webhook has avatar configured in Discord settings
2. Or set custom avatar with `DISCORD_AVATAR_URL`
3. Rebuild container if needed: `docker-compose build --no-cache`

---

## 🆕 Upgrading to v1.3.0 (from v1.2.0)

**Release Date:** October 27, 2025  
**Type:** Minor Release (New Features)  
**Breaking Changes:** None  
**Downtime:** ~1 minute

### What's New
- ✨ Email notifications support
- ✨ Automatic update checking
- ✨ Custom Discord webhook avatars
- ✨ Enhanced notification templates

### Optional New Features

#### 1. Email Notifications (Optional)

Add to your configuration if you want email notifications:

```yaml
environment:
  # Email Configuration (NEW in v1.3.0)
  EMAIL_ENABLED: "true"
  EMAIL_SMTP_HOST: "smtp.gmail.com"
  EMAIL_SMTP_PORT: "587"
  EMAIL_SMTP_USER: "your-email@gmail.com"
  EMAIL_SMTP_PASSWORD: "your-app-password"
  EMAIL_FROM: "wanwatcher@yourdomain.com"
  EMAIL_TO: "admin@yourdomain.com"
  EMAIL_USE_TLS: "true"
  EMAIL_SUBJECT_PREFIX: "[WANwatcher]"
```

**Gmail Users:** Use an [App Password](https://support.google.com/accounts/answer/185833)

#### 2. Update Checking (Optional)

```yaml
environment:
  # Update Check Configuration (NEW in v1.3.0)
  UPDATE_CHECK_ENABLED: "true"       # Default: true
  UPDATE_CHECK_INTERVAL: "86400"     # Check daily (in seconds)
  UPDATE_CHECK_ON_STARTUP: "true"    # Check on container start
```

#### 3. Custom Discord Avatar (Optional)

```yaml
environment:
  DISCORD_AVATAR_URL: "https://example.com/custom-avatar.png"
```

### Step-by-Step Upgrade

```bash
# 1. Backup current config
cp docker-compose.yml docker-compose.yml.backup

# 2. Pull new image
docker pull noxied/wanwatcher:1.3.0

# 3. Update docker-compose.yml (add new variables if desired)
nano docker-compose.yml

# 4. Restart
docker-compose down
docker-compose up -d

# 5. Check logs
docker-compose logs -f wanwatcher
```

### Verification

Check that everything still works:
- ✅ Existing Discord/Telegram notifications working
- ✅ New features available (if configured)
- ✅ No errors in logs

---

## 🆕 Upgrading to v1.2.0 (from v1.1.0 or earlier)

**Release Date:** October 15, 2024  
**Type:** Minor Release (New Features)  
**Breaking Changes:** None  
**Downtime:** ~1 minute

### What's New
- ✨ Telegram notifications
- ✨ IPv6 support
- ✨ Multiple IP detection services

### Optional New Features

#### 1. Telegram Notifications (Optional)

```yaml
environment:
  # Telegram Configuration (NEW in v1.2.0)
  TELEGRAM_ENABLED: "true"
  TELEGRAM_BOT_TOKEN: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
  TELEGRAM_CHAT_ID: "123456789"
  TELEGRAM_PARSE_MODE: "HTML"
```

**Setup:**
1. Create bot with [@BotFather](https://t.me/BotFather)
2. Get chat ID from [@userinfobot](https://t.me/userinfobot)

#### 2. IPv6 Monitoring (Optional)

```yaml
environment:
  # IPv6 Configuration (NEW in v1.2.0)
  MONITOR_IPV4: "true"  # Default: true
  MONITOR_IPV6: "true"  # Default: true (NEW!)
```

### Step-by-Step Upgrade

```bash
# 1. Backup
cp docker-compose.yml docker-compose.yml.backup

# 2. Pull new image
docker pull noxied/wanwatcher:1.2.0

# 3. Update config (optional new features)
nano docker-compose.yml

# 4. Restart
docker-compose down
docker-compose up -d

# 5. Verify
docker-compose logs -f wanwatcher
```

---

## 💾 Backup & Recovery

### Before Any Upgrade

```bash
# Backup database and logs
cp -r data data.backup
cp -r logs logs.backup

# Backup configuration
cp docker-compose.yml docker-compose.yml.backup
```

### If Something Goes Wrong

```bash
# Roll back to previous version
docker-compose down
docker pull noxied/wanwatcher:1.2.0  # Or your previous version
docker-compose up -d

# Restore data if needed
rm -rf data logs
mv data.backup data
mv logs.backup logs
```

---

## 🔄 Migration Paths

### From v1.0.0 to Latest (v1.3.1)

**Recommended:** Upgrade step-by-step through each version
1. v1.0.0 → v1.1.0
2. v1.1.0 → v1.2.0
3. v1.2.0 → v1.3.0
4. v1.3.0 → v1.3.1

**Alternative:** Direct upgrade to v1.3.1 (acceptable but test thoroughly)

### Configuration Evolution

**v1.0.0:**
```yaml
environment:
  DISCORD_WEBHOOK_URL: "..."
  SERVER_NAME: "My Server"
  CHECK_INTERVAL: "900"
```

**v1.3.1:**
```yaml
environment:
  # Discord (Enhanced in v1.3.0, v1.3.1)
  DISCORD_ENABLED: "true"           # NEW in v1.3.1
  DISCORD_WEBHOOK_URL: "..."        # v1.0.0
  DISCORD_AVATAR_URL: ""            # NEW in v1.3.0 (optional)
  
  # Telegram (NEW in v1.2.0)
  TELEGRAM_ENABLED: "false"
  TELEGRAM_BOT_TOKEN: ""
  TELEGRAM_CHAT_ID: ""
  
  # Email (NEW in v1.3.0)
  EMAIL_ENABLED: "false"
  EMAIL_SMTP_HOST: ""
  # ... more email config
  
  # General (v1.0.0, enhanced in later versions)
  SERVER_NAME: "My Server"
  CHECK_INTERVAL: "900"
  MONITOR_IPV4: "true"              # NEW in v1.2.0
  MONITOR_IPV6: "true"              # NEW in v1.2.0
  IPINFO_TOKEN: ""                  # NEW in v1.1.0 (optional)
```

---

## 🧪 Testing After Upgrade

### 1. Check Logs
```bash
docker-compose logs -f wanwatcher | head -50
```

**Look for:**
- ✅ Version number (should show new version)
- ✅ "Configured ✓" for enabled platforms
- ✅ No ERROR messages
- ✅ Successful notification sent

### 2. Trigger Test Notification

**Option A:** Change IP (simulated)
```bash
# Delete database to trigger "first run" notification
docker-compose down
sudo rm -f data/ipinfo.db
docker-compose up -d
```

**Option B:** Wait for next check interval

### 3. Verify Notifications

Check each enabled platform:
- ✅ Discord: Notification arrives with correct info
- ✅ Telegram: Message formatted correctly
- ✅ Email: Email received with proper formatting

---

## ❓ Common Upgrade Issues

### Issue: "Configuration not found" after upgrade

**Cause:** Environment variables not passed correctly

**Solution:**
```bash
# Check environment
docker exec wanwatcher env | grep DISCORD

# Restart with explicit config
docker-compose down
docker-compose up -d
```

### Issue: Notifications stop working after upgrade

**Cause:** New configuration flags required (v1.3.1+)

**Solution:**
```yaml
# Add missing flags
DISCORD_ENABLED: "true"    # Required in v1.3.1+
TELEGRAM_ENABLED: "false"  # or "true" if using
EMAIL_ENABLED: "false"     # or "true" if using
```

### Issue: Old version still running after pull

**Cause:** Image not updated

**Solution:**
```bash
# Force pull and rebuild
docker-compose pull
docker-compose down
docker rmi noxied/wanwatcher:old-version
docker-compose up -d
```

---

## 📞 Support

If you encounter issues during upgrade:

1. **Check logs:** `docker-compose logs wanwatcher`
2. **Review config:** Compare with examples in [README.md](README.md)
3. **GitHub Issues:** https://github.com/noxied/wanwatcher/issues
4. **Discussions:** https://github.com/noxied/wanwatcher/discussions

---

## 🔗 Additional Resources

- [README.md](README.md) - Full documentation
- [CHANGELOG.md](CHANGELOG.md) - Detailed version history
- [Troubleshooting Guide](docs/troubleshooting.md) - Common issues & solutions
- [GitHub Releases](https://github.com/noxied/wanwatcher/releases) - Release notes

---

**Always backup before upgrading!** 💾
