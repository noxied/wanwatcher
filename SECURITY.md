# Security Policy

## 🔒 Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## 🐛 Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please follow these guidelines:

### 📧 How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, report security vulnerabilities by:

1. **Opening a private security advisory:**
   - Go to https://github.com/noxied/wanwatcher/security/advisories/new
   - Fill out the form with details
   - We'll respond within 48 hours

2. **OR create a private issue** with the "security" label

### 📋 What to Include

Please include as much information as possible:

- **Type of vulnerability** (e.g., code injection, exposure of sensitive data)
- **Full paths of source file(s)** related to the vulnerability
- **Location of affected code** (tag/branch/commit or direct URL)
- **Step-by-step instructions** to reproduce the issue
- **Proof-of-concept or exploit code** (if possible)
- **Impact of the vulnerability** (what an attacker could do)
- **Suggested fix** (if you have one)

### ⏱️ Response Timeline

- **Initial response:** Within 48 hours
- **Status update:** Within 7 days
- **Fix timeline:** Depends on severity
  - **Critical:** Within 7 days
  - **High:** Within 30 days
  - **Medium:** Within 90 days
  - **Low:** Next regular release

### 🏆 Recognition

- We'll acknowledge your contribution in the security advisory
- Your name will be added to our security hall of fame (if you wish)
- We appreciate responsible disclosure!

---

## 🛡️ Security Best Practices

When using WANwatcher:

### Discord Webhook Security

- ✅ **Never share your webhook URL publicly**
- ✅ **Treat it like a password** - it provides write access to your Discord channel
- ✅ **Regenerate webhook** if accidentally exposed
- ✅ **Use environment variables** - never hardcode webhooks in files
- ✅ **Don't commit `.env` files** to git

### ipinfo.io Token Security

- ✅ **Keep your token private**
- ✅ **Use environment variables** for Docker
- ✅ **Don't commit tokens** to version control
- ✅ **Regenerate tokens** if exposed

### Docker Security

- ✅ **Use official images** from Docker Hub (`noxied/wanwatcher`)
- ✅ **Keep containers updated** - `docker pull` regularly
- ✅ **Run with limited resources** - use memory/CPU limits
- ✅ **Use read-only volumes** where possible
- ✅ **Don't run as root** (future improvement planned)

### Traditional Installation Security

- ✅ **Keep Python updated** to latest stable version
- ✅ **Install dependencies from official sources** only
- ✅ **Use virtual environments** to isolate dependencies
- ✅ **Set proper file permissions** on config files
- ✅ **Run as non-root user** when possible

### Network Security

- ✅ **Use HTTPS** for all webhook URLs (Discord uses HTTPS by default)
- ✅ **Firewall rules** - only allow necessary outbound connections
- ✅ **Monitor logs** for suspicious activity
- ✅ **Validate SSL certificates** (enabled by default in Python requests)

---

## 🔐 Known Security Considerations

### Discord Webhook URLs

**Risk:** Webhook URLs provide write access to Discord channels.

**Mitigation:**
- URLs are never logged or displayed in WANwatcher
- Store as environment variables (Docker) or in protected config files
- Regenerate webhooks immediately if exposed

### IP Address Exposure

**Risk:** Your WAN IP address is sent to Discord.

**Mitigation:**
- This is intentional behavior - monitor your Discord channel access
- Use private Discord channels
- Consider who has access to your Discord server

### Third-Party Services

**Dependencies:**
- Discord API (discord.com)
- IP detection services (api.ipify.org, ipapi.co, ifconfig.me)
- ipinfo.io (optional, for geographic data)

**Mitigation:**
- All use HTTPS
- Requests library validates SSL certificates
- Multiple fallback services for reliability

### Log Files

**Risk:** Logs may contain IP addresses and partial webhook URLs (for debugging).

**Mitigation:**
- Logs stored locally only
- Set proper file permissions
- Regularly rotate/clean logs
- Never share full logs publicly without redacting sensitive info

---

## 🔄 Security Updates

We'll announce security updates through:

1. **GitHub Security Advisories:** https://github.com/noxied/wanwatcher/security/advisories
2. **Release Notes:** Version-specific security fixes documented
3. **CHANGELOG.md:** Security fixes marked with `[SECURITY]`

To stay informed:
- Watch the repository for security advisories
- Check releases regularly
- Update to latest version promptly

---

## 📚 Additional Resources

- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [Docker Security](https://docs.docker.com/engine/security/)
- [Python Security](https://python.readthedocs.io/en/stable/library/security.html)
- [Discord Webhooks Security](https://discord.com/developers/docs/resources/webhook)

---

## ✅ Security Checklist for Users

Before deploying WANwatcher:

- [ ] Webhook URL stored securely (environment variable or protected file)
- [ ] ipinfo.io token stored securely (if used)
- [ ] Logs directory has proper permissions
- [ ] Using latest version
- [ ] Monitoring enabled (logs review)
- [ ] Discord channel access limited to trusted users
- [ ] Regular updates planned

---

## 🙏 Thank You

Thank you for helping keep WANwatcher and its users safe!

Security is everyone's responsibility. If you have suggestions for improving security, please open an issue or submit a pull request.

---

**Report Security Issues:** https://github.com/noxied/wanwatcher/security/advisories/new
