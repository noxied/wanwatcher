# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.0] - 2026-06-13

Reliability and code-quality hardening from the comprehensive review. No
configuration changes are required.

### Changed

- `/healthz` now returns 503 when the monitor loop has gone stale (no successful
  check within a generous multiple of `CHECK_INTERVAL`) instead of always 200,
  so a wedged loop is reported unhealthy. `/api/status` gains
  `seconds_since_last_check` and `check_interval`.
- Notification, DDNS, and MQTT failures during a check are now logged with stack
  traces and no longer counted as check failures; only detection failures drive
  outage detection and the adaptive backoff.
- The status snapshot served to the API is taken under a lock, preventing
  inconsistent reads while the loop updates state.

### Fixed

- A failed geo lookup no longer overwrites previously known geographic data.

### Internal

- mypy now runs with strict optional checking (removed `--no-strict-optional`);
  flake8 line length is aligned to 88 via a `.flake8` config; Dependabot now
  tracks pip dependencies.

## [2.4.1] - 2026-06-13

### Security

- Escape untrusted strings before placing them in notification bodies. Geo data
  from ipinfo.io (the `org`, `city`, `region`, and `timezone` fields) and GitHub
  release-note content are now HTML-escaped in email and Telegram
  (`parse_mode=HTML`) messages and markdown-escaped in Discord. This prevents
  markup or link injection into the notification channels. For Telegram it also
  fixes a case where a stray `<` or `&` in a field (for example the ISP `org`
  string) made the Bot API reject the message with a 400 error, silently
  dropping a real IP-change alert. Plain-text email and Apprise bodies were not
  affected and are unchanged.

## [2.4.0] - 2026-06-13

Supply-chain and provenance tooling. No application code changes; the image is
functionally identical to 2.3.0.

### Added

- OpenSSF Scorecard analysis runs in CI (weekly and on push to main),
  publishing results to the Security tab and the public OpenSSF API, with a
  badge in the README.
- The CycloneDX SBOM is now attached to each GitHub release as a downloadable
  asset, in addition to the per-run workflow artifact.

## [2.3.0] - 2026-06-13

### Added

- AWS Route53 DDNS provider (`DDNS_PROVIDER=route53`). Updates all configured
  records in a single atomic batch (UPSERT) using the Route53 REST API signed
  with Signature V4. No AWS SDK is bundled, so the image stays small. Configure
  with `ROUTE53_ACCESS_KEY_ID`, `ROUTE53_SECRET_ACCESS_KEY` (also supports the
  `_FILE` convention), `ROUTE53_HOSTED_ZONE_ID`, `ROUTE53_RECORDS`, and an
  optional `ROUTE53_TTL` (default 300). The credentials need
  `route53:ChangeResourceRecordSets` on the hosted zone.

## [2.2.0] - 2026-06-13

Security hardening. No breaking changes; existing configuration keeps working.

### Added

- Secrets can be read from files via the `<NAME>_FILE` convention (Docker and
  Kubernetes secret mounts) for every sensitive value: `DISCORD_WEBHOOK_URL`,
  `TELEGRAM_BOT_TOKEN`, `EMAIL_SMTP_PASSWORD`, `CLOUDFLARE_API_TOKEN`,
  `DUCKDNS_TOKEN`, `DYNDNS2_PASSWORD`, `MQTT_PASSWORD`, `IPINFO_TOKEN`, and
  `APPRISE_URLS`. A direct variable still wins; a `_FILE` path that does not
  exist stops startup with a clear error (fail-fast).
- Supply-chain security in CI: the built image is scanned with Trivy
  (HIGH/CRITICAL, unfixed ignored, with a `.trivyignore` for documented
  exceptions) before publishing; published images are signed with Cosign
  (keyless via Sigstore) by digest; a CycloneDX SBOM is generated and kept as a
  build artifact.

## [2.1.0] - 2026-06-13

Resilience and observability improvements. No breaking changes; all new
behaviour is either automatic or opt-in, and existing configuration keeps
working.

### Added

- Optional structured JSON logging (`LOG_FORMAT=json`). Each line is a single
  JSON object with a UTC ISO 8601 timestamp, level, logger name, and message,
  ready for aggregators such as Loki, Datadog, or Splunk. The default stays
  human-readable text. No new dependencies; the formatter is built on the
  standard library.

### Changed

- After a failed check the monitor now uses a short adaptive backoff (starting
  at 30 seconds, doubling, capped at `CHECK_INTERVAL`) instead of always
  waiting the full interval, so connectivity recovery is detected sooner. The
  steady-state interval is unchanged when checks succeed.
- Retry and backoff delays now include random jitter, so independent instances
  do not all retry on the same second (avoids synchronised request spikes
  against the detection and notification services).

## [2.0.0] - 2026-06-11

The application was restructured into a Python package (`wanwatcher/`). The old
`wanwatcher.py`, `wanwatcher_docker.py`, `notifications.py`, and
`config_validator.py` files are gone; the container now runs
`python -m wanwatcher`. Existing v1 environment variables keep working
unchanged and the state file is migrated automatically.

### Breaking

- The container runs as a non-root user (uid 1000). Host directories mounted
  on `/data` and `/logs` must be writable by uid 1000. When upgrading, run
  `sudo chown -R 1000:1000 ./data ./logs` (or equivalent) before starting the
  new image.
- The legacy standalone `wanwatcher.py` script was removed. The Docker image
  is the supported way to run WANwatcher.
- The image command changed from running a script to `python -m wanwatcher`.
  This only matters if you override the container CMD.

### Added

- Apprise notifications (`APPRISE_ENABLED`, `APPRISE_URLS`), which open up
  100+ services such as ntfy, Gotify, Pushover, Slack, and Matrix.
- Multi-source IP detection with source rotation, and confirmation of a
  detected change by a second independent source before notifying
  (`IP_CHANGE_CONFIRMATION`, on by default).
- Built-in dynamic DNS updates (`DDNS_ENABLED`, `DDNS_PROVIDER`) for
  Cloudflare (`CLOUDFLARE_*`), DuckDNS (`DUCKDNS_*`), and generic dyndns2
  providers (`DYNDNS2_*`). Failed updates are retried on the next check.
- HTTP status API (`API_ENABLED`, `API_BIND`, `API_PORT`) with `/healthz`,
  `/api/status`, and Prometheus `/metrics` endpoints.
- MQTT publishing (`MQTT_*`) with retained state topics, an availability
  topic, and Home Assistant auto-discovery.
- New events: startup notice (`NOTIFY_ON_STARTUP`), periodic heartbeat
  (`HEARTBEAT_ENABLED`, `HEARTBEAT_INTERVAL`), and internet outage detection
  with a recovery notification (`OUTAGE_DETECTION_ENABLED`,
  `OUTAGE_THRESHOLD`).
- The state file now keeps a history of the last 20 IP changes and a
  `last_change` timestamp.
- `HTTP_TIMEOUT` setting for outbound requests.

### Changed

- Whole codebase restructured into the `wanwatcher` package
  (`wanwatcher/notifiers/`, `wanwatcher/ddns/`, `wanwatcher/config.py`, ...).
- Graceful shutdown on SIGTERM: `docker stop` now exits promptly instead of
  waiting out the check interval (previously up to 15 minutes).
- The container healthcheck actually checks health: state file freshness and
  JSON validity, or `/healthz` when the API is enabled. Previously it only
  checked that the state file existed.
- State file writes are atomic (write to a temp file, then rename), so a
  crash mid-write cannot corrupt the state.
- Geographic lookups call the ipinfo.io HTTP API directly with `requests`.
- The old plain-text state format and the `update_notified.txt` sidecar file
  are absorbed into the JSON state file on first read.

### Removed

- `wanwatcher.py` (legacy standalone version) and its install scripts as a
  supported entry point.
- The `ipinfo` pip dependency.

### Security

- Container runs as a dedicated non-root user (uid 1000).
- Dependencies are pinned in `requirements.txt` (`requests`, `apprise`,
  `paho-mqtt`).
- The Telegram bot token is no longer embedded in stored URLs.
- Secrets (webhook URLs, tokens, passwords) are never written to logs;
  log output shows redacted forms only.

## [1.4.1] - 2025-11-02

### Changed

- Docker base image updated to Python 3.14; image size dropped from 51MB
  to 49MB.
- CI test matrix extended to Python 3.10 through 3.14.

### Fixed

- 65+ linting issues; formatting standardized via Black and isort.
- 8 CodeQL alerts resolved; explicit workflow permissions added.

## [1.4.0] - 2025-11-02

### Fixed

- Missing closing parenthesis in `wanwatcher.py:35` (`TELEGRAM_CHAT_ID`
  declaration) that prevented the standalone version from running.

### Added

- Configuration validator (`config_validator.py`), run before startup.
  Validates URLs (with HTTPS warnings), email addresses, ports (1-65535),
  Telegram token and chat id formats, Discord webhook URLs, and conflicting
  settings such as TLS and SSL both enabled. Can also be run standalone with
  `python config_validator.py`.
- Retry with exponential backoff for all notifications: up to 3 attempts
  with 1s, 2s, 4s delays, applied to Discord, Telegram, and email.
- IPv6 validation using the `ipaddress` module. Loopback, link-local,
  multicast, private/ULA, and reserved addresses are rejected; only globally
  routable addresses are accepted. A third IPv6 detection service was added.
- Test suite with 109+ cases across `tests/test_config_validator.py`,
  `tests/test_ip_validation.py`, and `tests/test_notifications.py`, with
  coverage reporting.
- GitHub Actions CI: Black, isort, Flake8, Pylint, MyPy, Bandit, Safety,
  pytest on Python 3.10-3.12, config validation, multi-platform Docker
  builds (AMD64, ARM64), automatic push on tags/main, and release creation
  from the changelog.
- Dependabot configuration.
- Type hints on all major functions, checked with MyPy.
- `requirements-dev.txt` and `pytest.ini`.

### Changed

- Version strings synchronized across all files.
- Clearer error messages for configuration problems, retry attempts, and
  IPv6 validation decisions.

This release is backward compatible; no configuration changes required.

## [1.3.3] - 2025-10-29

### Fixed

- Version references updated from 1.3.2 to 1.3.3 in `wanwatcher_docker.py`,
  `wanwatcher.py`, and `notifications.py`.

Patch release correcting version numbers only; no functional changes from
1.3.2.

## [1.3.2] - 2025-10-29

### Fixed

- Email template converted to Gmail-compatible inline styles. Gmail strips
  `<style>` tags, which broke the custom CSS; all styling now uses inline
  `style=""` attributes. Also fixed a duplicate header caused by malformed
  HTML and made the template mobile-friendly.
- Email variable names corrected in README.md (18 instances):
  `EMAIL_SMTP_SERVER` is actually `EMAIL_SMTP_HOST`, `EMAIL_USERNAME` is
  `EMAIL_SMTP_USER`, `EMAIL_PASSWORD` is `EMAIL_SMTP_PASSWORD`. The code
  always expected the correct names; the README was wrong.
- Hardcoded version strings removed from notification templates; the
  current version is now passed in as a parameter.
- `wanwatcher.py` (non-Docker) renamed its variables to match the Docker
  version: `ENABLE_EMAIL` to `EMAIL_ENABLED`, `ENABLE_TELEGRAM` to
  `TELEGRAM_ENABLED`, `ENABLE_DISCORD` to `DISCORD_ENABLED`, and `SMTP_*`
  to `EMAIL_SMTP_*`.

### Migration from 1.3.1

If you configured email following README examples from 1.3.1 or earlier,
rename these variables:

```yaml
# old (never worked)        # correct
EMAIL_SMTP_SERVER:    ->    EMAIL_SMTP_HOST:
EMAIL_USERNAME:       ->    EMAIL_SMTP_USER:
EMAIL_PASSWORD:       ->    EMAIL_SMTP_PASSWORD:
```

Docker images are functionally identical to 1.3.1 apart from the template
and version display fixes.

## [1.3.1] - 2025-10-28

### Fixed

- Discord avatar handling now respects the webhook's configured avatar. The
  base64 data URL approach was removed (not supported by the Discord API).
- Version display synchronized across notification templates.

### Added

- `DISCORD_ENABLED` environment variable, matching the existing
  `TELEGRAM_ENABLED` and `EMAIL_ENABLED` flags.
- `DISCORD_AVATAR_URL` for an optional custom avatar.

## [1.3.0] - 2025-10-27

### Added

- Email notifications over SMTP with TLS/SSL support, HTML and plain-text
  templates, multiple recipients, and a configurable subject prefix.
  New variables: `EMAIL_ENABLED`, `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`,
  `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_TO`,
  `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_SUBJECT_PREFIX`.
- Update checking against GitHub releases with a configurable interval.
  New variables: `UPDATE_CHECK_ENABLED`, `UPDATE_CHECK_INTERVAL`,
  `UPDATE_CHECK_ON_STARTUP`.
- Custom Discord webhook avatars.

## [1.2.0] - 2024-10-15

### Added

- Telegram notifications via bot token and chat id, with HTML and Markdown
  formatting. New variables: `TELEGRAM_ENABLED`, `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`, `TELEGRAM_PARSE_MODE`.
- IPv6 monitoring alongside IPv4, each controllable independently.
  New variables: `MONITOR_IPV4`, `MONITOR_IPV6`.

### Changed

- IP detection uses multiple fallback services.
- Improved error handling and structured logging.

## [1.1.0] - 2024-08-20

### Added

- Optional geographic data via ipinfo.io: city, region, country,
  ISP/organization, timezone. New variables: `IPINFO_TOKEN`, `BOT_NAME`.
- Docker health check based on the state file.

### Changed

- Improved Discord embed layout and timestamp formatting.

## [1.0.0] - 2024-06-01

Initial release.

- Discord webhook notifications on WAN IP change.
- Docker deployment with persistent storage and log files.
- IP detection with multiple fallback services and a configurable check
  interval. Variables: `DISCORD_WEBHOOK_URL`, `SERVER_NAME`,
  `CHECK_INTERVAL`, `IP_DB_FILE`, `LOG_FILE`.

## License

MIT, see [LICENSE](LICENSE).
