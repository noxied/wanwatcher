# Changelog

All notable changes to WANwatcher will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-10-26

### Added
- **Telegram Bot Support** - Send notifications via Telegram bot
  - HTML formatted messages
  - Configurable parse mode (HTML or Markdown)
  - Chat ID and bot token configuration
- **Multi-Platform Notification System** - New architecture supporting multiple notification providers
  - `NotificationProvider` abstract base class
  - `DiscordNotifier` class for Discord webhooks
  - `TelegramNotifier` class for Telegram bots
  - `NotificationManager` class for managing multiple providers
- **Notification Module** - Separate `notifications.py` module for clean architecture
- **Version Display** - All notifications now include WANwatcher version
  - Version shown in Environment field
  - Version shown in notification footer
  - Version shown in error notifications
- **New Environment Variables**:
  - `TELEGRAM_ENABLED` - Enable/disable Telegram notifications
  - `TELEGRAM_BOT_TOKEN` - Telegram bot token
  - `TELEGRAM_CHAT_ID` - Telegram chat ID for notifications
  - `TELEGRAM_PARSE_MODE` - Message format (HTML or Markdown)

### Changed
- **Discord Notification Layout** - Improved spacing and readability
  - Fixed spacing between Current and Previous IPv4 fields
  - Added proper 3-column layout for better visual organization
  - Enhanced embed structure
- **Error Notifications** - Now sent to all configured notification platforms
- **Startup Logs** - More detailed information about configured notification providers

### Fixed
- Discord embed spacing issue between IP address fields
- Missing version information in notifications
- Notification layout inconsistencies

### Security
- Documented security best practices for token/webhook management
- Added warnings about not committing secrets to version control

---

## [1.1.0] - 2025-10-25

### Added
- **IPv6 Support** - Full monitoring of IPv6 addresses
  - Separate detection for IPv6
  - Configurable IPv6 monitoring via `MONITOR_IPV6`
  - IPv6 change detection and notifications
- **Dual IP Monitoring** - Track both IPv4 and IPv6 simultaneously
  - New database format supporting both protocols
  - Automatic migration from old format
- **Enhanced Notifications** - Rich embeds showing both IPv4 and IPv6
  - Color-coded notifications (green for initial, orange for changes)
  - Detailed change information
  - Separate fields for current and previous IPs
- **Configuration Options**:
  - `MONITOR_IPV4` - Enable/disable IPv4 monitoring
  - `MONITOR_IPV6` - Enable/disable IPv6 monitoring

### Changed
- Database format now stores both IPv4 and IPv6 as JSON
- Notification embeds restructured for dual-protocol support
- Log messages enhanced with both IPv4 and IPv6 information

### Fixed
- Backward compatibility with old database format
- IP detection fallback mechanisms improved

---

## [1.0.0] - 2025-10-24

### Added
- Initial release of WANwatcher
- **IPv4 Monitoring** - Automatic WAN IPv4 address detection
- **Discord Notifications** - Rich embed notifications via Discord webhooks
- **Geographic Data** - Optional ipinfo.io integration
  - City, region, country detection
  - ISP information
  - Timezone information
- **Docker Support** - Optimized for containerized environments
  - Continuous loop monitoring mode
  - Persistent database storage
  - Log file persistence
  - Health checks
- **Configuration via Environment Variables**:
  - `DISCORD_WEBHOOK_URL` - Discord webhook
  - `IPINFO_TOKEN` - ipinfo.io API token
  - `SERVER_NAME` - Server identification
  - `BOT_NAME` - Bot display name
  - `CHECK_INTERVAL` - Monitoring frequency
- **IP Detection Services** - Multiple fallback services
  - api.ipify.org
  - ipapi.co
  - ifconfig.me
  - api.myip.com
- **Error Handling** - Automatic recovery and error notifications
- **Resource Efficiency** - Minimal memory and CPU usage
- **Multi-Architecture** - AMD64 and ARM64 support

### Security
- No exposed ports required
- Secure handling of webhook URLs
- Isolated container environment

---

## Release Notes

### v1.2.0 Highlights

This release brings **Telegram support** to WANwatcher! You can now receive notifications on Telegram in addition to (or instead of) Discord. The notification system has been refactored with a provider architecture, making it easy to add more platforms in the future.

**Key Features:**
- 📱 Telegram bot notifications with beautiful HTML formatting
- 🔔 Use Discord, Telegram, or both platforms simultaneously
- 🎨 Improved Discord notification layout
- 📦 Version tracking in all notifications

**Upgrade Notes:**
- Existing Discord-only users: No changes needed, everything works as before
- To add Telegram: Set `TELEGRAM_ENABLED="true"` and configure bot token/chat ID
- New `notifications.py` module is automatically included in the Docker image

**Breaking Changes:** None - fully backward compatible with v1.1.0

---

## Future Roadmap

### v1.3.0 (Planned)
- Slack notification support
- Email notification support
- More notification providers

### v2.0.0 (Planned)
- Web dashboard
- Historical IP tracking
- Multiple server monitoring
- Alerting rules and filters
- API endpoints

---

## Versioning

WANwatcher follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version (X.0.0): Incompatible API changes
- **MINOR** version (0.X.0): New features, backward compatible
- **PATCH** version (0.0.X): Bug fixes, backward compatible

---

## Links

- [GitHub Repository](https://github.com/noxied/wanwatcher)
- [Docker Hub](https://hub.docker.com/r/noxied/wanwatcher)
- [Issue Tracker](https://github.com/noxied/wanwatcher/issues)
- [Releases](https://github.com/noxied/wanwatcher/releases)
