# Contributing to WANwatcher

Thank you for your interest in contributing to WANwatcher! 🎉

This document provides guidelines for contributing to the project.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Pull Requests](#pull-requests)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)

---

## 📜 Code of Conduct

This project follows a simple code of conduct:

- **Be respectful** - Treat everyone with respect
- **Be constructive** - Provide helpful feedback
- **Be patient** - Remember that people have different skill levels
- **Be inclusive** - Welcome newcomers

---

## 🤝 How Can I Contribute?

### Reporting Bugs

Found a bug? Please help us fix it!

**Before submitting a bug report:**
- Check the [existing issues](https://github.com/noxied/wanwatcher/issues) to avoid duplicates
- Try the latest version to see if the bug still exists
- Collect information about your setup

**How to submit a good bug report:**

1. Use the bug report template (if available)
2. Include a clear, descriptive title
3. Describe the expected vs actual behavior
4. Provide steps to reproduce
5. Include logs (redact sensitive info!)
6. Specify your environment:
   - OS and version
   - Docker version (if using Docker)
   - Python version (if traditional)
   - WANwatcher version

**Example:**

```markdown
**Description:** Container exits immediately after starting

**Expected:** Container should run continuously

**Actual:** Container stops after 2 seconds

**Steps to Reproduce:**
1. Run: docker run -d -e DISCORD_WEBHOOK_URL="..." noxied/wanwatcher:latest
2. Check: docker ps -a
3. Container shows as "Exited"

**Logs:**
```
[paste logs here]
```

**Environment:**
- OS: Ubuntu 22.04
- Docker: 24.0.7
- WANwatcher: 1.0.0
```

---

## 💡 Suggesting Features

Have an idea for a new feature?

**Before suggesting:**
- Check [existing issues](https://github.com/noxied/wanwatcher/issues) for similar suggestions
- Consider if it fits the project scope

**How to suggest a feature:**

1. Open a new issue with a clear title
2. Describe the feature in detail
3. Explain the use case / why it's useful
4. Provide examples if possible
5. Consider implementation challenges

**Example:**

```markdown
**Feature:** Add Telegram notification support

**Use Case:** 
Users who prefer Telegram over Discord should be able to receive notifications via Telegram bot.

**Proposed Implementation:**
- Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables
- Create telegram notification function similar to Discord webhook
- Allow both Discord and Telegram simultaneously

**Benefits:**
- More notification options
- Broader user base
- Similar implementation to Discord

**Considerations:**
- Need to handle Telegram API rate limits
- Requires python-telegram-bot library
- Should be optional (not required)
```

---

## 🔧 Pull Requests

Ready to contribute code? Awesome!

### Before You Start

1. **Fork the repository**
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
   or
   ```bash
   git checkout -b fix/bug-description
   ```

### Making Changes

1. **Make your changes** in your branch
2. **Test thoroughly** - Make sure it works!
3. **Update documentation** if needed
4. **Keep commits focused** - One logical change per commit
5. **Write clear commit messages**

**Good commit messages:**
```
Add Telegram notification support

- Add telegram bot integration
- Update environment variables documentation
- Add telegram example to README
```

**Bad commit messages:**
```
fixed stuff
update
changes
```

### Submitting Pull Request

1. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub

3. **Fill out the PR description:**
   - What does this PR do?
   - Why is this change needed?
   - How was it tested?
   - Screenshots (if UI changes)
   - Related issues (if any)

4. **Wait for review** - Be patient and responsive to feedback

### PR Checklist

Before submitting, make sure:
- [ ] Code follows project style
- [ ] Changes are tested
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No sensitive information in code
- [ ] PR description is complete

---

## 💻 Development Setup

### Traditional Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/wanwatcher.git
cd wanwatcher

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install requests

# Optional: Install ipinfo
pip install ipinfo

# Run the script
python3 wanwatcher.py
```

### Docker Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/wanwatcher.git
cd wanwatcher

# Build local image
docker build -t wanwatcher-dev .

# Test the image
docker run --rm \
  -e DISCORD_WEBHOOK_URL="your_webhook" \
  wanwatcher-dev
```

### Testing Changes

**Manual Testing:**

1. Test traditional installation:
   ```bash
   ./scripts/install.sh
   python3 /root/wanwatcher/wanwatcher.py
   ```

2. Test Docker:
   ```bash
   docker build -t wanwatcher-test .
   docker run --rm -e DISCORD_WEBHOOK_URL="..." wanwatcher-test
   ```

3. Test different scenarios:
   - First run (no previous IP)
   - IP change
   - Network errors
   - Invalid webhook
   - With/without ipinfo token

---

## 🎨 Code Style

### Python Style

Follow PEP 8 guidelines:

- **Indentation:** 4 spaces (no tabs)
- **Line length:** Max 100 characters (prefer 80)
- **Naming:**
  - Variables/functions: `snake_case`
  - Constants: `UPPER_CASE`
  - Classes: `PascalCase`

**Example:**

```python
# Good
def get_current_ip():
    """Get current WAN IP address"""
    try:
        response = requests.get(IP_SERVICE_URL, timeout=10)
        return response.json()['ip']
    except Exception as e:
        logging.error(f"Failed to get IP: {e}")
        return None

# Bad
def GetCurrentIP():
    response=requests.get(IP_SERVICE_URL)
    return response.json()['ip']
```

### Documentation

- **Docstrings** for all functions
- **Comments** for complex logic
- **Clear variable names** (no single letters except loops)

### Shell Scripts

- Use `#!/bin/bash`
- Add comments for complex commands
- Use `set -e` for error handling
- Quote variables: `"$VARIABLE"`

---

## 🧪 Testing

Currently, WANwatcher doesn't have automated tests (contributions welcome!).

### Manual Testing Checklist

Before submitting PR, test:

**Docker:**
- [ ] Build succeeds
- [ ] Container starts without errors
- [ ] Notifications work
- [ ] Logs are readable
- [ ] Data persists in volumes
- [ ] Environment variables work

**Traditional:**
- [ ] Installation script works
- [ ] Script runs without errors
- [ ] Notifications work
- [ ] Cron job works
- [ ] Logs are created
- [ ] Database is created

**Both:**
- [ ] IP detection works
- [ ] Discord webhook works
- [ ] Error handling works
- [ ] Log output is clear

---

## 📝 Documentation

When contributing, please update documentation:

### README.md
- Add new features to Features section
- Update configuration table if adding env vars
- Add examples for new functionality

### Docker
- Update Dockerfile if changing dependencies
- Update docker-compose.yml if adding env vars

### Comments
- Add docstrings to new functions
- Comment complex logic
- Keep comments up to date

---

## ❓ Questions?

- **General questions:** Open a [GitHub Issue](https://github.com/noxied/wanwatcher/issues)
- **Bugs:** Use bug report template
- **Features:** Open feature request issue
- **Security issues:** See SECURITY.md (if available) or open a private issue

---

## 🎉 First Time Contributing?

Welcome! We love first-time contributors!

**Easy ways to contribute:**
- Fix typos in documentation
- Improve error messages
- Add code comments
- Test on different platforms
- Improve README examples
- Translate documentation

**Don't be afraid to ask questions!** Everyone was a beginner once. 😊

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## 🙏 Thank You!

Your contributions make WANwatcher better for everyone!

Every contribution counts:
- ⭐ Starring the repo
- 🐛 Reporting bugs
- 💡 Suggesting features
- 📝 Improving docs
- 🔧 Submitting code

Thank you for being part of the community! 🚀
