# WANwatcher Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.4.0] - 2025-01-30

### 🎉 Major Quality & Reliability Release

This release focuses on making WANwatcher production-ready with comprehensive testing, validation, and improved reliability.

### 🐛 Critical Fixes
- **CRITICAL - Syntax Error:** Fixed missing closing parenthesis in wanwatcher.py:35
  - `TELEGRAM_CHAT_ID` variable declaration was malformed
  - Prevented standalone version from running
  - Now properly loads Telegram configuration

### ✨ New Features

#### Configuration Validation System
- **NEW:** Comprehensive configuration validator (`config_validator.py`)
  - Validates all environment variables before startup
  - URL format validation with HTTPS enforcement warnings
  - Email address validation with proper regex
  - Port number validation (1-65535 range)
  - Telegram token and chat ID format validation
  - Discord webhook URL validation
  - Detects conflicting settings (e.g., TLS + SSL both enabled)
  - Integrated into startup sequence - fails fast with clear errors
- **Run standalone:** `python config_validator.py`

#### Notification Retry Logic
- **NEW:** Exponential backoff retry system for all notifications
  - Automatically retries failed notifications up to 3 times
  - Backoff delays: 1s → 2s → 4s
  - Works with Discord, Telegram, and Email
  - Detailed logging of retry attempts
  - Significantly reduces notification loss during temporary outages

#### Enhanced IPv6 Validation
- **NEW:** Proper IPv6 address validation using Python's `ipaddress` module
  - Validates IPv6 format correctly (not just checking for colons)
  - Filters out special-use addresses:
    - Loopback addresses (::1)
    - Link-local addresses (fe80::/10)
    - Multicast addresses (ff00::/8)
    - Private/ULA addresses (fc00::/7, fd00::/8)
    - Reserved addresses
  - Only accepts public, globally routable IPv6 addresses
  - Added third IPv6 detection service for better reliability
- **Function:** `is_valid_ipv6()` in wanwatcher_docker.py

### 🧪 Testing Infrastructure

#### Unit Test Suite
- **NEW:** Comprehensive test suite with 109+ test cases
  - `tests/test_config_validator.py` - 92 test cases for configuration validation
  - `tests/test_ip_validation.py` - 11 test cases for IPv6 validation
  - `tests/test_notifications.py` - 6+ test cases for notification system
  - Coverage reporting with pytest-cov
  - Mock testing for external services
- **Run tests:** `pytest tests/ -v --cov`

#### CI/CD Pipeline
- **NEW:** GitHub Actions workflow (`.github/workflows/ci.yml`)
  - **Linting:** Black, isort, Flake8, Pylint, MyPy
  - **Security:** Bandit security scanning, Safety dependency checks
  - **Testing:** Pytest on Python 3.10, 3.11, 3.12
  - **Config Validation:** Validates example configurations
  - **Docker Build:** Multi-platform (AMD64, ARM64) automated builds
  - **Docker Push:** Automatic on tags and main branch
  - **GitHub Releases:** Automatic release creation with changelog
- **NEW:** Dependabot configuration for automated dependency updates

### 📝 Type Hints
- **Added:** Comprehensive type hints to all major functions
  - Better IDE autocomplete and intellisense
  - Catches type errors before runtime
  - Self-documenting code
  - Enables MyPy static type checking
- **Examples:**
  ```python
  def get_ipv6() -> Optional[str]
  def get_current_ips() -> Tuple[Dict[str, Optional[str]], Optional[Dict[str, Any]]]
  def check_ip() -> bool
  ```

### 🛠 Improved

#### Version Consistency
- Updated all files to version 1.4.0:
  - wanwatcher_docker.py
  - wanwatcher.py
  - notifications.py
  - Dockerfile
  - docker-compose.yml

#### Error Messages
- Configuration errors now show exactly what's wrong
- IPv6 validation provides detailed debug logging
- Retry logic logs each attempt with timing
- Clearer startup validation messages

#### Development Experience
- **NEW:** `requirements-dev.txt` - Development dependencies
- **NEW:** `pytest.ini` - Pytest configuration
- **NEW:** `RELEASE_NOTES_v1.4.0.md` - Detailed release documentation
- Enhanced `.gitignore` - Added test artifacts and type checker caches

### 🔒 Security
- Input validation prevents malformed configuration
- HTTPS enforcement warnings for webhook URLs
- Email address format validation
- Port range validation
- Telegram token format validation

### 📚 Documentation
- **NEW:** Comprehensive release notes (RELEASE_NOTES_v1.4.0.md)
- Updated README with v1.4.0 features
- Migration guide for upgrading from v1.3.x
- Type hints serve as inline documentation

### 🏗 Technical Improvements
- Multi-architecture Docker builds (AMD64, ARM64)
- Automated CI/CD pipeline
- Code coverage reporting
- Static type checking with MyPy
- Security scanning with Bandit
- Dependency vulnerability scanning with Safety

### 📊 Statistics
- **Files Changed:** 15+
- **New Files Created:** 10
- **Lines of Code Added:** ~2,500
- **Test Cases:** 109+
- **Type Hints Added:** 15+ functions
- **Critical Bugs Fixed:** 1

### ⬆️ Upgrade Notes
**This release is fully backward compatible.** No configuration changes required.

Simply update your Docker image:
```bash
docker pull noxied/wanwatcher:1.4.0
docker-compose restart
```

See [UPGRADING.md](UPGRADING.md) for detailed upgrade instructions.

### 🎯 Next Steps
Future potential improvements (not in this release):
- Web dashboard for monitoring
- Additional notification platforms (Slack, Pushover, ntfy.sh)
- Historical IP change tracking with SQLite
- Export functionality (CSV, JSON)
- Multi-server monitoring from single instance

---

## [1.3.3] - 2025-10-29

### 🛠 Fixed
- **Version Consistency:** Updated all version references from 1.3.2 to 1.3.3
  - Fixed version number in wanwatcher_docker.py
  - Fixed version number in wanwatcher.py
  - Fixed version number in notifications.py
  - Ensures consistent version display across all components

### 📝 Documentation
- Updated CHANGELOG.md with complete version history
- Updated UPGRADING.md with v1.3.3 upgrade notes

**Note:** This is a patch release that corrects version numbering. No functional changes from v1.3.2.

---

## [1.3.2] - 2025-10-29

### 🐛 Fixed
- **CRITICAL - Email Template:** Converted email HTML to Gmail-compatible inline styles
  - Gmail strips `<style>` tags from emails, breaking custom CSS
  - Converted all CSS to inline `style=""` attributes that Gmail respects
  - Email notifications now properly display dark theme (#2c2c2c background)
  - Fixed duplicate header issue caused by malformed HTML (removed lines 601-624)
  - Implemented professional dark theme with proper contrast
  - Email template now mobile-responsive with proper scaling
  - Reduced email size by 15% (more efficient inline styles)
- **CRITICAL - Documentation:** Fixed email variable names in README.md (18 instances)
  - Corrected `EMAIL_SMTP_SERVER` → `EMAIL_SMTP_HOST`
  - Corrected `EMAIL_USERNAME` → `EMAIL_SMTP_USER`
  - Corrected `EMAIL_PASSWORD` → `EMAIL_SMTP_PASSWORD`
  - These corrections fix email configuration issues for users following README examples
- **CRITICAL - Version Display:** Fixed hardcoded version strings in notification templates
  - All notifications now dynamically display the current version
  - Prevents version mismatch confusion (e.g., showing v1.3.1 after upgrading to v1.3.2)
  - Updated notifications.py to accept version parameter instead of hardcoding
- **Consistency:** Updated wanwatcher.py (non-Docker) to use consistent variable names
  - Changed `ENABLE_EMAIL` → `EMAIL_ENABLED`
  - Changed `ENABLE_TELEGRAM` → `TELEGRAM_ENABLED`
  - Changed `ENABLE_DISCORD` → `DISCORD_ENABLED`
  - Changed `SMTP_*` variables → `EMAIL_SMTP_*` variables
  - Ensures consistency between Docker and non-Docker versions

### 📝 Documentation
- **README.md:** Corrected all email configuration examples throughout the document
- **TROUBLESHOOTING.md:** Added comprehensive email/SMTP troubleshooting section
  - Gmail app password setup guide
  - Common SMTP configuration issues
  - Port and TLS/SSL configuration examples
  - Variable name corrections guide
- **UPGRADING.md:** Added v1.3.2 upgrade notes and migration instructions
- **CHANGELOG.md:** Complete version history documentation

### ⚠️ Migration from v1.3.1

If you configured email following README.md examples from v1.3.1 or earlier, update your configuration:

**Old (incorrect) variable names:**
```yaml
EMAIL_SMTP_SERVER: "smtp.gmail.com"     # ❌ Wrong
EMAIL_USERNAME: "user@example.com"      # ❌ Wrong  
EMAIL_PASSWORD: "password"              # ❌ Wrong
```

**New (correct) variable names:**
```yaml
EMAIL_SMTP_HOST: "smtp.gmail.com"       # ✅ Correct
EMAIL_SMTP_USER: "user@example.com"     # ✅ Correct
EMAIL_SMTP_PASSWORD: "password"         # ✅ Correct
```

**Note:** Docker images are functionally identical to v1.3.1. Only documentation corrections and version display improvements included.

---

## [1.3.1] - 2025-10-28

### 🐛 Bug Fixes
- **Discord Notifications:** Fixed avatar URL handling to respect webhook configuration
  - Removed base64 data URL approach (not supported by Discord API)
  - Now uses webhook's configured avatar by default
  - Added optional `DISCORD_AVATAR_URL` environment variable for custom avatars
- **Version Display:** Fixed hardcoded version strings in notification templates
  - Updated all notification templates from v1.3.0 to v1.3.1
  - Ensures consistent version display across all platforms

### 🔧 Added
- **Discord Configuration:** Added `DISCORD_ENABLED` environment variable
  - Provides explicit enable/disable flag for Discord notifications
  - Matches naming convention with `TELEGRAM_ENABLED` and `EMAIL_ENABLED`
  - Improves configuration consistency across all notification platforms

### ⚙️ Changed
- **Discord Avatar Handling:** Improved avatar configuration
  - By default, uses webhook's configured avatar (set in Discord webhook settings)
  - Custom avatar URL can be provided via `DISCORD_AVATAR_URL` environment variable
  - Simplified avatar logic and removed embedded base64 encoding

### 📝 Documentation
- Updated configuration examples
- Added Discord avatar configuration guide
- Improved troubleshooting documentation

---

## [1.3.0] - 2025-10-27

### ✨ Added
- **Email Notifications:** Full email notification support
  - SMTP configuration with TLS/SSL support
  - HTML and plain text email templates
  - Multiple recipient support
  - Customizable subject prefix
- **Custom Discord Avatars:** Support for custom webhook avatars
  - Optional `DISCORD_AVATAR_URL` environment variable
  - Embedded avatar support for Docker images
- **Update Notifications:** Automatic update checking
  - Configurable check interval
  - Notifications when new versions available
  - GitHub release integration
  - Can be enabled/disabled per notification platform

### 🔧 Configuration Changes
- Added `EMAIL_ENABLED` environment variable
- Added `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT` variables
- Added `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASSWORD` variables
- Added `EMAIL_FROM`, `EMAIL_TO` variables
- Added `EMAIL_USE_TLS`, `EMAIL_USE_SSL` variables
- Added `EMAIL_SUBJECT_PREFIX` variable
- Added `UPDATE_CHECK_ENABLED` variable
- Added `UPDATE_CHECK_INTERVAL` variable
- Added `UPDATE_CHECK_ON_STARTUP` variable

### 📝 Documentation
- Comprehensive README update
- Email configuration guide
- Update check configuration guide
- Migration guide from v1.2.0

---

## [1.2.0] - 2024-10-15

### ✨ Added
- **Telegram Notifications:** Full Telegram bot support
  - Telegram bot token and chat ID configuration
  - HTML and Markdown formatting support
  - Detailed IP change notifications
- **IPv6 Support:** Monitor both IPv4 and IPv6 addresses
  - Separate IPv4 and IPv6 detection
  - Configurable monitoring per protocol
  - Independent change tracking

### 🔧 Configuration Changes
- Added `TELEGRAM_ENABLED` environment variable
- Added `TELEGRAM_BOT_TOKEN` environment variable
- Added `TELEGRAM_CHAT_ID` environment variable
- Added `TELEGRAM_PARSE_MODE` environment variable
- Added `MONITOR_IPV4` environment variable
- Added `MONITOR_IPV6` environment variable

### ⚙️ Changed
- Improved IP detection with multiple fallback services
- Enhanced error handling and recovery
- Better logging with structured output

### 📝 Documentation
- Added Telegram setup guide
- Added IPv6 configuration guide
- Improved Docker Compose examples

---

## [1.1.0] - 2024-08-20

### ✨ Added
- **Geographic Data:** Optional ipinfo.io integration
  - City, region, country information
  - ISP/Organization details
  - Timezone information
- **Health Checks:** Docker health check support
  - Database file validation
  - Container status monitoring

### 🔧 Configuration Changes
- Added `IPINFO_TOKEN` environment variable
- Added `BOT_NAME` environment variable
- Improved `SERVER_NAME` handling

### ⚙️ Changed
- Enhanced Discord embed formatting
- Improved notification content layout
- Better timestamp formatting

---

## [1.0.0] - 2024-06-01

### ✨ Initial Release
- **Discord Notifications:** Webhook-based notifications
  - Rich embed formatting
  - IP change detection
  - Server identification
- **Docker Support:** Containerized deployment
  - Persistent data storage
  - Log file management
  - Environment variable configuration
- **IP Detection:** Automatic WAN IP monitoring
  - Multiple fallback services
  - Configurable check intervals
  - First-run detection

### 🔧 Configuration
- `DISCORD_WEBHOOK_URL` environment variable
- `SERVER_NAME` environment variable
- `CHECK_INTERVAL` environment variable
- `IP_DB_FILE` for persistent storage
- `LOG_FILE` for logging

---

## Version History Summary

- **v1.3.1** (2025-10-28) - Bug fixes for Discord notifications and version display
- **v1.3.0** (2025-10-27) - Email notifications, update checking, custom avatars
- **v1.2.0** (2024-10-15) - Telegram notifications, IPv6 support
- **v1.1.0** (2024-08-20) - Geographic data, health checks
- **v1.0.0** (2024-06-01) - Initial release

---

## Migration Guides

### From v1.3.0 to v1.3.1
- **Required:** Add `DISCORD_ENABLED` environment variable (set to `"true"` to enable Discord)
- **Optional:** Remove `DISCORD_AVATAR_URL` if using webhook's default avatar
- **Note:** Existing configurations will continue to work, but adding `DISCORD_ENABLED` is recommended

### From v1.2.0 to v1.3.0
- **Optional:** Configure email notifications (see README for full setup)
- **Optional:** Enable update checking with `UPDATE_CHECK_ENABLED="true"`
- **Note:** All v1.2.0 configurations remain compatible

### From v1.1.0 to v1.2.0
- **Optional:** Configure Telegram (see README for bot setup)
- **Optional:** Enable IPv6 monitoring with `MONITOR_IPV6="true"`
- **Note:** Discord configurations remain unchanged

---

## Support

- **Issues:** https://github.com/noxied/wanwatcher/issues
- **Discussions:** https://github.com/noxied/wanwatcher/discussions
- **Documentation:** https://github.com/noxied/wanwatcher

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
