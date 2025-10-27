# Changelog

All notable changes to WANwatcher will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2025-XX-XX

### Added
- **Email Notifications** 📧 - Send alerts via SMTP (Gmail, Outlook, custom SMTP)
- HTML formatted emails with professional responsive design
- Plain text email fallback for compatibility
- Support for multiple email recipients (comma-separated)
- TLS/SSL support for secure SMTP connections
- **Custom Discord Webhook Avatars** 🎨 - Set custom avatar URL or use embedded default
- Embedded default avatar (`wan_watcher.png`) included in Docker image
- Email-specific error handling and logging
- Gmail app password documentation

### Changed
- Updated all product descriptions from "Discord notifications" to "Multi-platform notifications"
- Dockerfile labels updated to reflect Discord, Telegram, and Email support
- README.md updated with email configuration instructions
- docker-compose.yml updated with email configuration section
- Improved notification provider initialization

### New Environment Variables
- `EMAIL_ENABLED` - Enable/disable email notifications (default: false)
- `EMAIL_SMTP_HOST` - SMTP server hostname
- `EMAIL_SMTP_PORT` - SMTP port (587 for TLS, 465 for SSL)
- `EMAIL_SMTP_USER` - SMTP username (usually email address)
- `EMAIL_SMTP_PASSWORD` - SMTP password or app password
- `EMAIL_FROM` - From email address
- `EMAIL_TO` - To email address(es), comma-separated for multiple
- `EMAIL_USE_TLS` - Use TLS encryption (recommended)
- `EMAIL_USE_SSL` - Use SSL encryption (alternative to TLS)
- `EMAIL_SUBJECT_PREFIX` - Customize email subject prefix (default: "[WANwatcher]")
- `DISCORD_AVATAR_URL` - Custom Discord webhook avatar URL (optional)

### Fixed
- Improved SMTP error handling
- Better email connection timeout handling
- Enhanced notification provider error logging

---

## [1.2.0] - 2025-10-26

### Added
- **Telegram Bot Support** - Receive notifications via Telegram
- Multi-platform notification architecture
- `notifications.py` module with provider pattern
- HTML formatted Telegram messages
- **Version Display** - All notifications now show version number
- Notification provider abstraction layer
- Comprehensive Telegram documentation

### Changed
- Improved Discord embed layout and spacing
- Better formatted notification messages
- Enhanced error handling
- Updated Docker image labels

### New Environment Variables
- `TELEGRAM_ENABLED` - Enable/disable Telegram notifications
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `TELEGRAM_CHAT_ID` - Your Telegram chat ID
- `TELEGRAM_PARSE_MODE` - Message format (HTML or Markdown)

### Security
- Added SECURITY.md with best practices
- Environment variable security documentation
- Secrets management guidelines
- `.gitignore` for sensitive files

---

## [1.1.0] - 2025-10-25

### Added
- **IPv6 Support** - Monitor both IPv4 and IPv6 addresses
- Configurable IPv4/IPv6 monitoring via environment variables
- Improved IP change detection logic
- Better null handling for IP addresses

### Changed
- Updated notification format to display both IPv4 and IPv6
- Improved logging messages
- Enhanced error handling

### New Environment Variables
- `MONITOR_IPV4` - Enable/disable IPv4 monitoring (default: true)
- `MONITOR_IPV6` - Enable/disable IPv6 monitoring (default: true)

---

## [1.0.0] - 2025-10-24

### Added
- Initial release
- Docker containerized WAN IP monitoring
- Discord webhook notifications
- Automatic IP change detection
- Geographic data integration via ipinfo.io
- Configurable check intervals
- Persistent IP storage
- Health checks
- Comprehensive logging
- Multi-stage Docker build
- Docker Compose support

### Features
- IPv4 monitoring
- Discord embed notifications
- Database persistence
- Error recovery
- Fallback IP services
- Resource limits
- Log rotation
- Timezone aware timestamps

---

## Release Notes

### v1.3.0 - Email & Avatar Support
The third major release adds comprehensive email notification support with beautiful HTML templates, making WANwatcher a complete multi-platform notification system. Custom Discord avatars allow for better branding and identification.

**Key Highlights:**
- 📧 Professional HTML emails
- 🎨 Custom Discord avatars
- 📱 Three notification platforms
- 🔐 Secure SMTP (TLS/SSL)
- 📨 Multiple recipients
- ✅ Backward compatible

### v1.2.0 - Telegram Integration
The second major release adds Telegram bot support, creating a flexible multi-platform notification system. Users can now choose Discord, Telegram, or both platforms simultaneously.

**Key Highlights:**
- 💬 Telegram bot notifications
- 🔀 Multi-platform architecture
- 📦 Version tracking
- 🎨 Improved Discord layout
- 🔒 Enhanced security

### v1.1.0 - IPv6 Support
First feature update adding IPv6 monitoring capabilities, doubling the monitoring coverage for modern networks.

**Key Highlights:**
- 🌐 IPv6 monitoring
- ⚙️ Configurable protocols
- 📊 Dual-stack support

### v1.0.0 - Initial Release
First stable release of WANwatcher, providing reliable WAN IP monitoring with Discord notifications in a Docker container.

**Key Highlights:**
- 🐳 Docker ready
- 📢 Discord notifications
- 🌍 Geographic data
- 🔄 Auto-recovery
- 📝 Comprehensive logs

---

## Upgrade Paths

### From v1.2.0 to v1.3.0
- ✅ Fully backward compatible
- Add Email environment variables (optional)
- Add Discord avatar URL (optional)
- Pull new image and restart
- See [UPGRADING.md](UPGRADING.md) for details

### From v1.1.0 to v1.3.0
- ✅ Fully backward compatible
- Telegram support available (optional)
- Email support available (optional)
- Pull new image and restart
- Consider removing IP database for initial notification

### From v1.0.0 to v1.3.0
- ✅ Fully backward compatible
- Add IPv4/IPv6 monitoring variables
- Add Telegram support (optional)
- Add Email support (optional)
- Pull new image and restart

---

## Links

- **GitHub Repository**: https://github.com/noxied/wanwatcher
- **Docker Hub**: https://hub.docker.com/r/noxied/wanwatcher
- **Documentation**: See [README.md](README.md)
- **Security**: See [SECURITY.md](SECURITY.md)
- **Upgrading**: See [UPGRADING.md](UPGRADING.md)

---

[1.3.0]: https://github.com/noxied/wanwatcher/releases/tag/v1.3.0
[1.2.0]: https://github.com/noxied/wanwatcher/releases/tag/v1.2.0
[1.1.0]: https://github.com/noxied/wanwatcher/releases/tag/v1.1.0
[1.0.0]: https://github.com/noxied/wanwatcher/releases/tag/v1.0.0
