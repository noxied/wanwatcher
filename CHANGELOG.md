# Changelog

All notable changes to WANwatcher will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Telegram notification support
- Slack notification support
- Email notification support
- Web dashboard
- Historical data charts and graphs
- Kubernetes deployment guide
- Additional notification platforms

---

## [1.1.0] - 2025-10-25

### Added
- **IPv6 Support** - Monitor both IPv4 and IPv6 addresses simultaneously
  - Monitor both protocols at once or individually
  - Separate fallback services for IPv6 detection (api64.ipify.org, api6.ipify.org)
  - Configurable IPv4/IPv6 monitoring via environment variables
  - Enhanced Discord notifications showing both IPv4 and IPv6 addresses
  - Backward compatible with v1.0.0 database format
  
- **Multi-Architecture Docker Support**
  - Native AMD64 (x86_64) support for most servers and desktops
  - Native ARM64 (aarch64) support for Raspberry Pi 4, modern ARM servers
  - Single `docker pull` command automatically selects correct architecture
  - Optimized builds for each platform
  
- **New Environment Variables**
  - `MONITOR_IPV4` - Enable/disable IPv4 monitoring (default: true)
  - `MONITOR_IPV6` - Enable/disable IPv6 monitoring (default: true)
  
- **Enhanced Discord Notifications**
  - Beautiful embeds displaying both IPv4 and IPv6 information
  - Separate fields for current and previous addresses for each protocol
  - Visual indicators showing which protocol changed
  - Status messages for unavailable protocols
  - Improved Discord timestamp formatting
  
- **Database Improvements**
  - JSON-based storage format for multiple IP addresses
  - Automatic migration from v1.0.0 plain-text format
  - Support for storing both IPv4 and IPv6 simultaneously
  - Backward compatibility maintained

### Changed
- Updated Discord notification layout to accommodate dual-stack addressing
- Improved logging to show IPv4 and IPv6 detection separately
- Enhanced error messages for protocol-specific failures
- Updated documentation with IPv6 configuration examples

### Platform Support
All platforms from v1.0.0 plus:
- Raspberry Pi (all models with ARM64 support)
- ARM-based NAS systems
- Apple Silicon Macs (via Docker Desktop)
- Any ARM64 Linux system

---

## [1.0.0] - 2025-10-25

### Added
- Initial release of WANwatcher
- Discord webhook notifications with rich embeds
- Docker support with pre-built images
- Traditional installation with automated installer
- Geographic information via ipinfo.io integration
- Multiple fallback IP detection services for IPv4
- Comprehensive error handling and logging
- Configurable check intervals
- Data persistence across restarts
- Support for multiple platforms (Linux, Docker, NAS systems, Raspberry Pi)
- Complete documentation (README, installation guides)
- MIT License
- Installation scripts for traditional deployment
- Docker Compose configuration
- Environment variable configuration for Docker
- Automatic IP change detection
- Initial run detection
- Continuous monitoring mode for Docker
- Cron integration for traditional deployment
- Health check support in Docker
- Resource limits and optimization
- JSON-based logging

### Features
- IPv4 address detection using multiple services
- Discord rich embed notifications
- Optional geographic data (city, region, country, ISP, timezone)
- Persistent IP storage in SQLite-like flat file
- Automatic retry on failures
- Clean shutdown handling
- Docker health checks
- Volume support for data and logs
- Configurable via environment variables

### Platform Support
- Linux (all distributions)
- Docker / Docker Compose
- TrueNAS Scale
- Synology NAS
- QNAP NAS
- Unraid
- Raspberry Pi (via Docker on ARM64)
- Windows (via Docker Desktop)
- macOS (via Docker Desktop)

---

## Legend

- `Added` - New features
- `Changed` - Changes in existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Vulnerability fixes

---

[Unreleased]: https://github.com/noxied/wanwatcher/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/noxied/wanwatcher/releases/tag/v1.1.0
[1.0.0]: https://github.com/noxied/wanwatcher/releases/tag/v1.0.0
