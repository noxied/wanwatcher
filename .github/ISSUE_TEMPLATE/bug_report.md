---
name: Bug Report
about: Report a bug or issue with WANwatcher
title: '[BUG] '
labels: bug
assignees: ''
---

## 🐛 Bug Description

A clear and concise description of the bug.

## 📋 Expected Behavior

What you expected to happen.

## 💥 Actual Behavior

What actually happened.

## 🔄 Steps to Reproduce

1. Go to '...'
2. Run command '...'
3. See error

## 📊 Environment

**Deployment Method:** (Docker / Traditional)

**If Docker:**
- Docker Version: 
- Docker Compose Version: 
- Image Tag: 

**If Traditional:**
- OS: 
- Python Version: 
- Installation Method: 

**WANwatcher Version:** 

**Platform:** (TrueNAS / Synology / Unraid / Linux / etc.)

## 📝 Configuration

**Environment Variables (Docker):**
```yaml
DISCORD_WEBHOOK_URL: "[REDACTED]"
SERVER_NAME: "My Server"
CHECK_INTERVAL: "900"
IPINFO_TOKEN: "[REDACTED or NOT SET]"
```

**Or Traditional Config:**
```python
SERVER_NAME = "My Server"
# Other relevant config...
```

## 📋 Logs

**Container Logs (Docker):**
```
[Paste logs here - REDACT webhook URLs and tokens!]
```

**Or Script Output (Traditional):**
```
[Paste output here - REDACT sensitive info!]
```

**Log File Contents:**
```
[Paste relevant log entries - REDACT sensitive info!]
```

## 📸 Screenshots

If applicable, add screenshots to help explain the problem.

## 🔍 Additional Context

Any other context about the problem here.

## ✅ Checklist

- [ ] I've checked existing issues for duplicates
- [ ] I'm using the latest version
- [ ] I've included all relevant information
- [ ] I've redacted sensitive information (webhook URLs, tokens, IPs)
- [ ] I've included logs
