# Security Policy

## 🔐 Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.4.x   | ✅ Yes (Current)  |
| 1.3.x   | ✅ Yes            |
| 1.2.x   | ⚠️ Limited (critical fixes only) |
| < 1.2   | ❌ No             |

## 🛡️ Security Best Practices

### Never Commit Secrets

**DO NOT** commit the following to version control:
- ❌ Discord webhook URLs
- ❌ Telegram bot tokens
- ❌ Telegram chat IDs
- ❌ ipinfo.io API tokens
- ❌ Any credentials or API keys

### ✅ Safe Configuration Methods

**Option 1: Environment Variables (Recommended)**
```bash
export DISCORD_WEBHOOK_URL="your_webhook"
export TELEGRAM_BOT_TOKEN="your_token"
docker run -e DISCORD_WEBHOOK_URL -e TELEGRAM_BOT_TOKEN wanwatcher
```

**Option 2: .env File (Local Development)**
```bash
# Create .env file (add to .gitignore!)
echo "DISCORD_WEBHOOK_URL=your_webhook" > .env
echo "TELEGRAM_BOT_TOKEN=your_token" >> .env

# Use with docker-compose
docker-compose --env-file .env up -d
```

**Option 3: Docker Secrets (Production)**
```bash
# Create secrets
echo "your_webhook" | docker secret create discord_webhook -
echo "your_token" | docker secret create telegram_token -

# Use in docker-compose.yml
secrets:
  - discord_webhook
  - telegram_token
```

**Option 4: Portainer/Kubernetes Secrets**
- Use built-in secret management
- Never expose secrets in YAML files

### ❌ Bad Practices to Avoid

```yaml
# DON'T DO THIS - Committing secrets to git
environment:
  DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/1234/abcd"
  TELEGRAM_BOT_TOKEN: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
```

```yaml
# DON'T DO THIS - Hardcoding in Dockerfile
ENV DISCORD_WEBHOOK_URL="https://discord.com/..."
```

### ✅ Good Practices

```yaml
# DO THIS - Use placeholders in git
environment:
  DISCORD_WEBHOOK_URL: "${DISCORD_WEBHOOK_URL}"
  TELEGRAM_BOT_TOKEN: "${TELEGRAM_BOT_TOKEN}"
```

```yaml
# DO THIS - Reference external secrets
environment:
  DISCORD_WEBHOOK_URL: "your_webhook_here_configure_in_portainer"
```

## 🔍 Security Considerations

### Network Security

**WANwatcher Network Requirements:**
- ✅ Outbound HTTPS (443) to:
  - Discord API (discord.com)
  - Telegram API (api.telegram.org)
  - IP detection services (api.ipify.org, etc.)
  - ipinfo.io (if configured)
- ❌ No inbound ports required
- ❌ No exposed services

**Recommendations:**
- Use Docker networks for isolation
- Consider firewall rules limiting outbound connections
- Monitor container network activity

### Webhook/Token Security

**Discord Webhooks:**
- Treat webhook URLs as passwords
- Anyone with the URL can send messages to your channel
- Regenerate webhooks if compromised
- Use Discord audit logs to monitor usage

**Telegram Bots:**
- Bot tokens provide full control of the bot
- Rotate tokens if compromised
- Use @BotFather to revoke/regenerate tokens
- Only share Chat ID with trusted parties

**ipinfo.io Tokens:**
- Free tier has rate limits
- Don't share tokens publicly
- Monitor usage for suspicious activity

### Container Security

**Best Practices:**
- ✅ Run as non-root user (if possible)
- ✅ Use specific version tags (not :latest) in production
- ✅ Scan images for vulnerabilities
- ✅ Keep base images updated
- ✅ Limit container resources
- ✅ Use read-only file systems where possible

**Example Secure Configuration:**
```yaml
services:
  wanwatcher:
    image: noxied/wanwatcher:1.2.0  # Specific version
    read_only: true  # Read-only filesystem
    security_opt:
      - no-new-privileges:true  # Prevent privilege escalation
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 128M
```

### Data Security

**Database File:**
- Contains your current/previous IP addresses
- Not sensitive but could reveal location
- Stored in `/data/ipinfo.db`
- Consider encrypting volume if needed

**Log Files:**
- May contain IP addresses
- Stored in `/logs/`
- Rotate and clean old logs regularly
- Don't expose log directory publicly

### Secrets Rotation

**Recommended Schedule:**
- Discord Webhooks: Every 6-12 months or when compromised
- Telegram Tokens: Every 6-12 months or when compromised
- ipinfo.io Tokens: Yearly or when approaching rate limits

**How to Rotate:**

1. **Discord Webhook:**
   - Create new webhook in Discord
   - Update `DISCORD_WEBHOOK_URL`
   - Restart container
   - Delete old webhook

2. **Telegram Bot:**
   - Message @BotFather
   - Use `/revoke` command
   - Get new token
   - Update `TELEGRAM_BOT_TOKEN`
   - Restart container

3. **ipinfo.io Token:**
   - Generate new token at ipinfo.io
   - Update `IPINFO_TOKEN`
   - Restart container
   - Revoke old token

## 🚨 Reporting a Vulnerability

If you discover a security vulnerability in WANwatcher:

1. **DO NOT** open a public issue
2. **DO NOT** disclose publicly until fixed
3. **DO** email: [240063414+noxied@users.noreply.github.com]
4. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

**Response Time:**
- Acknowledgment: Within 48 hours
- Initial assessment: Within 1 week
- Fix timeline: Depends on severity

**Severity Levels:**
- **Critical:** Fix within 24-48 hours
- **High:** Fix within 1 week
- **Medium:** Fix within 1 month
- **Low:** Fix in next release

## ✅ Security Checklist

Before deploying WANwatcher:

- [ ] All secrets stored securely (not in git)
- [ ] Using specific version tags (not :latest)
- [ ] Webhook/token access restricted
- [ ] Container resources limited
- [ ] Logs properly secured
- [ ] Network access restricted to required services
- [ ] Regular update schedule planned
- [ ] Backup/recovery plan in place
- [ ] Monitoring configured
- [ ] Documentation read and understood

## 📚 Additional Resources

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Discord API Security](https://discord.com/developers/docs/topics/oauth2)
- [Telegram Bot Security](https://core.telegram.org/bots#6-botfather)

## 🔄 Security Updates

Subscribe to security updates:
- Watch the GitHub repository
- Follow releases
- Enable Dependabot alerts (for maintainers)

---

**Remember: Security is a shared responsibility. While we strive to make WANwatcher secure, proper configuration and deployment practices are essential.**
