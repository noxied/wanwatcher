# Troubleshooting Guide

Common issues and solutions for WANwatcher.

---

## 📋 Table of Contents

- [Docker Issues](#docker-issues)
- [Traditional Installation Issues](#traditional-installation-issues)
- [Discord Webhook Issues](#discord-webhook-issues)
- [IP Detection Issues](#ip-detection-issues)
- [Network Issues](#network-issues)
- [Platform-Specific Issues](#platform-specific-issues)

---

## 🐳 Docker Issues

### Container Exits Immediately

**Symptoms:**
- Container shows as "Exited" right after starting
- `docker ps` doesn't show the container
- `docker ps -a` shows "Exited (1)"

**Check logs:**
```bash
docker logs wanwatcher
```

**Common Causes:**

#### 1. Missing DISCORD_WEBHOOK_URL

**Error:**
```
FATAL: DISCORD_WEBHOOK_URL environment variable is not set!
```

**Solution:**
```bash
# Verify webhook is set
docker inspect wanwatcher | grep DISCORD_WEBHOOK_URL

# If missing, recreate container with webhook
docker rm wanwatcher
docker run -d \
  --name wanwatcher \
  -e DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." \
  noxied/wanwatcher:latest
```

#### 2. Invalid Webhook URL

**Error:**
```
Failed to send Discord notification: 404 Not Found
```

**Solution:**
- Check webhook still exists in Discord
- Verify URL is complete and correct
- Test webhook manually:
  ```bash
  curl -X POST \
    -H "Content-Type: application/json" \
    -d '{"content":"Test"}' \
    "YOUR_WEBHOOK_URL"
  ```

#### 3. Network Issues

**Error:**
```
Failed to retrieve IP from all services
```

**Solution:**
```bash
# Test container network
docker exec wanwatcher ping -c 4 8.8.8.8

# Check DNS
docker exec wanwatcher nslookup api.ipify.org

# Try recreating with host network
docker run -d \
  --name wanwatcher \
  --network host \
  -e DISCORD_WEBHOOK_URL="..." \
  noxied/wanwatcher:latest
```

### Container Unhealthy

**Check health status:**
```bash
docker inspect wanwatcher | grep -A 20 "Health"
```

**Common causes:**
- Container just started (wait 30 seconds)
- Volume permissions issues
- Database file can't be created

**Solution:**
```bash
# Check volume permissions
ls -la data/

# Fix permissions if needed
chmod 755 data/

# Restart container
docker restart wanwatcher
```

### No Logs in Log File

**Check:**
```bash
# See if logs directory exists
ls -la logs/

# Check docker logs
docker logs wanwatcher
```

**Solution:**
```bash
# Ensure volumes are mounted correctly
docker inspect wanwatcher | grep -A 10 "Mounts"

# If using relative paths, use absolute:
docker run -d \
  --name wanwatcher \
  -v /full/path/to/data:/data \
  -v /full/path/to/logs:/logs \
  noxied/wanwatcher:latest
```

### High Memory Usage

**Check usage:**
```bash
docker stats wanwatcher
```

**Expected:** 50-60MB  
**If higher:** May indicate issue

**Solution:**
```bash
# Restart container
docker restart wanwatcher

# If persists, check logs for errors
docker logs wanwatcher | grep -i error

# Set memory limit
docker update --memory="128m" wanwatcher
```

---

## 💻 Traditional Installation Issues

### "No module named 'requests'"

**Error:**
```python
ModuleNotFoundError: No module named 'requests'
```

**Solution:**

**Option 1: Using pip:**
```bash
pip3 install requests --break-system-packages
# or
sudo pip3 install requests
```

**Option 2: Manual installation:**
```bash
# Download requests
cd /tmp
wget https://files.pythonhosted.org/packages/.../requests-2.31.0.tar.gz
tar -xzf requests-2.31.0.tar.gz
cd requests-2.31.0
sudo python3 setup.py install
```

### Cron Job Not Running

**Check if cron is installed:**
```bash
service cron status
# or
systemctl status cron
```

**Install cron if needed:**
```bash
sudo apt install cron
sudo systemctl enable cron
sudo systemctl start cron
```

**Check cron logs:**
```bash
grep CRON /var/log/syslog
# or
journalctl -u cron
```

**Verify crontab:**
```bash
crontab -l
```

**Test script manually:**
```bash
python3 /root/wanwatcher/wanwatcher.py
```

**Common issues:**

#### 1. Path Issues

**Bad:**
```bash
*/15 * * * * python3 wanwatcher.py
```

**Good:**
```bash
*/15 * * * * /usr/bin/python3 /root/wanwatcher/wanwatcher.py >> /var/log/wanwatcher-cron.log 2>&1
```

#### 2. Permissions

```bash
# Make script executable
chmod +x /root/wanwatcher/wanwatcher.py

# Check directories exist and are writable
ls -la /var/lib/wanwatcher
ls -la /var/log/wanwatcher.log
```

### Permission Denied

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/var/lib/wanwatcher/ipinfo.db'
```

**Solution:**
```bash
# Create directories
sudo mkdir -p /var/lib/wanwatcher
sudo mkdir -p /var/log

# Set permissions
sudo chmod 755 /var/lib/wanwatcher

# Or run script with sudo
sudo python3 /root/wanwatcher/wanwatcher.py
```

---

## 🔔 Discord Webhook Issues

### 404 Not Found

**Cause:** Webhook was deleted or URL is wrong

**Solution:**
1. Go to Discord → Server Settings → Integrations → Webhooks
2. Check if webhook exists
3. Create new webhook if needed
4. Copy new URL
5. Update configuration

### 401 Unauthorized

**Cause:** Invalid webhook URL or token

**Solution:**
- Verify entire URL is copied (including token at end)
- URL should look like: `https://discord.com/api/webhooks/123456789/AbCdEfGhIjKlMnOpQrStUvWxYz`

### No Notifications Received

**Test webhook manually:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"content":"Test from WANwatcher"}' \
  "YOUR_WEBHOOK_URL"
```

**If manual test works but script doesn't:**

1. **Check logs:**
   ```bash
   # Docker
   docker logs wanwatcher | grep -i discord
   
   # Traditional
   cat /var/log/wanwatcher.log | grep -i discord
   ```

2. **Check IP actually changed:**
   ```bash
   # Docker
   cat data/ipinfo.db
   
   # Traditional
   cat /var/lib/wanwatcher/ipinfo.db
   ```

3. **Force IP change for testing:**
   ```bash
   # Docker
   docker exec wanwatcher rm /data/ipinfo.db
   docker restart wanwatcher
   
   # Traditional
   sudo rm /var/lib/wanwatcher/ipinfo.db
   python3 /root/wanwatcher/wanwatcher.py
   ```

### Rate Limiting

**Error:**
```
429 Too Many Requests
```

**Cause:** Too many notifications sent too quickly

**Solution:**
- Discord webhooks have rate limits
- Increase CHECK_INTERVAL
- Don't run multiple instances with same webhook

---


---

## 📧 Email/SMTP Issues

### Email Notifications Not Working

**Check configuration:**
```bash
docker logs wanwatcher | grep -i email
```

**Look for:**
- `Email: Configured ✓` - Working!
- `Email: Enabled but missing SMTP configuration ✗` - Configuration error
- `Email: Not enabled` - EMAIL_ENABLED not set to true

### Common Issues

#### 1. Wrong Variable Names (README v1.3.1 and earlier)

**Problem:** Following old README examples with incorrect variable names

**Symptoms:**
```
Email: Enabled but missing SMTP configuration ✗
```

**Solution - Use CORRECT variable names:**
```yaml
EMAIL_ENABLED: "true"
EMAIL_SMTP_HOST: "smtp.gmail.com"
EMAIL_SMTP_USER: "user@example.com"
EMAIL_SMTP_PASSWORD: "your_password"
EMAIL_FROM: "from@example.com"
EMAIL_TO: "to@example.com"
```

#### 2. Gmail App Password Required

**Error:** Username and Password not accepted

**Solution:**
1. Go to Google Account Security
2. Enable 2-Step Verification
3. Generate App Password
4. Use the 16-character app password as EMAIL_SMTP_PASSWORD

#### 3. Port/TLS Configuration

**Gmail:**
```yaml
EMAIL_SMTP_HOST: "smtp.gmail.com"
EMAIL_SMTP_PORT: "587"
EMAIL_USE_TLS: "true"
```

**Outlook:**
```yaml
EMAIL_SMTP_HOST: "smtp-mail.outlook.com"
EMAIL_SMTP_PORT: "587"
EMAIL_USE_TLS: "true"
```

#### 4. Testing Email

```bash
# Delete database to trigger notification
docker exec wanwatcher rm /data/ipinfo.db
docker restart wanwatcher
```

## 🌐 IP Detection Issues

### "Failed to retrieve IP from all services"

**Causes:**
- No internet connection
- All IP services are down (very rare)
- Firewall blocking requests
- DNS issues

**Diagnosis:**

```bash
# Test internet connectivity
ping -c 4 8.8.8.8

# Test DNS
nslookup api.ipify.org

# Test IP services manually
curl https://api.ipify.org?format=json
curl https://ipapi.co/json
curl https://ifconfig.me/all.json
```

**Solutions:**

1. **Check firewall:**
   ```bash
   # Check if firewall is blocking
   sudo ufw status
   
   # Allow outbound if needed
   sudo ufw allow out 443/tcp
   ```

2. **Check proxy settings:**
   ```bash
   echo $http_proxy
   echo $https_proxy
   ```

3. **Try different IP service:**
   Edit script to try different services first

### ipinfo.io Issues

**Error:**
```
Failed to get geographic data
```

**Common causes:**
- Invalid API token
- Token expired
- Rate limit exceeded (50k/month on free tier)

**Solutions:**

1. **Verify token:**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" https://ipinfo.io/
   ```

2. **Check rate limit:**
   - Log in to ipinfo.io
   - Check usage dashboard

3. **Disable if not needed:**
   ```bash
   # Docker: Don't set IPINFO_TOKEN
   # Traditional: Set IPINFO_TOKEN = ""
   ```

---

## 🌍 Network Issues

### Docker Container Can't Reach Internet

**Test:**
```bash
docker exec wanwatcher ping -c 4 8.8.8.8
docker exec wanwatcher ping -c 4 google.com
```

**Solutions:**

1. **Use host network:**
   ```bash
   docker run -d \
     --name wanwatcher \
     --network host \
     -e DISCORD_WEBHOOK_URL="..." \
     noxied/wanwatcher:latest
   ```

2. **Check Docker daemon DNS:**
   ```bash
   # Edit /etc/docker/daemon.json
   {
     "dns": ["8.8.8.8", "8.8.4.4"]
   }
   
   # Restart Docker
   sudo systemctl restart docker
   ```

3. **Check firewall:**
   ```bash
   sudo iptables -L
   ```

### Behind Proxy

**Docker:**
```bash
docker run -d \
  --name wanwatcher \
  -e HTTP_PROXY="http://proxy:port" \
  -e HTTPS_PROXY="http://proxy:port" \
  -e DISCORD_WEBHOOK_URL="..." \
  noxied/wanwatcher:latest
```

**Traditional:**
```bash
export http_proxy="http://proxy:port"
export https_proxy="http://proxy:port"
python3 /root/wanwatcher/wanwatcher.py
```

---

## 🖥️ Platform-Specific Issues

### TrueNAS Scale

**Issue:** Container stops after TrueNAS reboot

**Solution:**
- Ensure restart policy is set to `unless-stopped`
- Check Portainer stack configuration

**Issue:** Can't access logs

**Solution:**
```bash
# SSH to TrueNAS
ssh root@truenas-ip

# Find container
docker ps | grep wanwatcher

# View logs
docker logs wanwatcher
```

### Synology NAS

**Issue:** Permission denied on volumes

**Solution:**
1. Create folder in File Station first
2. Set proper permissions
3. Use absolute paths in Container Manager

### Raspberry Pi

**Issue:** Wrong architecture

**Solution:**
- Use multi-arch image: `noxied/wanwatcher:latest`
- Image should work on ARM/ARM64 automatically

**If build fails:**
```bash
# Build for ARM on Pi
docker build -t wanwatcher:latest .
```

---

## 🔍 Debugging Tips

### Enable Debug Logging

Currently not available, but you can:

```bash
# Docker - follow logs
docker logs -f wanwatcher

# Traditional - watch log file
tail -f /var/log/wanwatcher.log
```

### Check What's Running

```bash
# Docker
docker ps -a | grep wanwatcher
docker inspect wanwatcher

# Traditional
ps aux | grep wanwatcher
crontab -l | grep wanwatcher
```

### Verify Configuration

```bash
# Docker
docker inspect wanwatcher | grep -A 20 Env

# Traditional
cat /root/wanwatcher/wanwatcher.py | grep -E "(DISCORD_WEBHOOK_URL|SERVER_NAME)"
```

---

## 🆘 Still Having Issues?

If you've tried everything above:

1. **Check existing issues:** https://github.com/noxied/wanwatcher/issues
2. **Open a new issue:** Use the bug report template
3. **Include:**
   - Full logs (redact sensitive info!)
   - Your configuration
   - Steps you've already tried
   - Platform/environment details

---

## 📚 Additional Resources

- [README](../README.md) - Main documentation
- [CHANGELOG](../CHANGELOG.md) - Version history
- [UPGRADING](../UPGRADING.md) - Upgrade guide

---

**Most issues can be resolved by checking logs and verifying configuration!** 🔍
