# Changelog

All notable changes to WANwatcher will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- IPv6 support
- Telegram notification support
- Slack notification support
- Email notification support
- Web dashboard
- Historical data charts
- Kubernetes deployment guide

---

## [1.0.0] - 2025-10-25

### Added
- Initial release of WANwatcher
- Discord webhook notifications with rich embeds
- Docker support with pre-built images
- Traditional installation with automated installer
- Geographic information via ipinfo.io integration
- Multiple fallback IP detection services
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

### Platform Support
- Linux (all distributions)
- Docker / Docker Compose
- TrueNAS Scale
- Synology NAS
- QNAP NAS
- Unraid
- Raspberry Pi (ARM/ARM64)
- Windows (via Docker Desktop)
- macOS (via Docker Desktop)

---

## Version History

### [1.0.0] - 2025-10-25
- 🎉 Initial stable release

---

## Legend

- `Added` - New features
- `Changed` - Changes in existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Vulnerability fixes

---

[Unreleased]: https://github.com/noxied/wanwatcher/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/noxied/wanwatcher/releases/tag/v1.0.0
