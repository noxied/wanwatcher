# WANwatcher

![WANwatcher Banner](https://raw.githubusercontent.com/noxied/wanwatcher/main/wanwatcher-banner.png)

Monitors your WAN IPv4/IPv6 addresses and tells you when they change. When an
address changes it can notify you, update DNS records, publish the state over
MQTT for Home Assistant, and expose a status API with Prometheus metrics. It is
aimed at homelabs and small servers on connections where the ISP changes your IP.

[![GitHub Release](https://img.shields.io/github/v/release/noxied/wanwatcher)](https://github.com/noxied/wanwatcher/releases)
[![Docker Pulls](https://img.shields.io/docker/pulls/noxied/wanwatcher)](https://hub.docker.com/r/noxied/wanwatcher)
[![Docker Image Size](https://img.shields.io/docker/image-size/noxied/wanwatcher/latest)](https://hub.docker.com/r/noxied/wanwatcher)
[![License](https://img.shields.io/github/license/noxied/wanwatcher)](https://github.com/noxied/wanwatcher/blob/main/LICENSE)

---

## Recent releases

- 2.5.0: reliability hardening (stuck-loop /healthz, isolated notifier failures, locked status reads).
- 2.4.1: security fix - escape untrusted geo/release-note strings in notifications.
- 2.3.0: AWS Route53 DDNS provider (SigV4, no AWS SDK bundled).
- 2.2.0: secrets from files (`<NAME>_FILE`), plus Trivy scanning, CycloneDX SBOM and Cosign keyless image signing.
- 2.1.0: optional JSON logging (`LOG_FORMAT=json`) and adaptive backoff with jitter.
- 2.0.0: rebuilt as a Python package with Apprise, multi-source detection, DDNS, status API/metrics, MQTT/Home Assistant, events, and a non-root container.

Coming from 1.x, the one breaking change is that the container runs as uid 1000,
so the `/data` and `/logs` volumes must be writable by that user. See the
[upgrade guide](https://github.com/noxied/wanwatcher/blob/main/UPGRADING.md).

[Full changelog](https://github.com/noxied/wanwatcher/blob/main/CHANGELOG.md)

---

## Features

Notifications
- Discord webhooks with embeds
- Telegram bot messages
- Email over SMTP with HTML and plain-text bodies
- Apprise, covering 100+ services from one `APPRISE_URLS` setting

IP detection
- IPv4 and IPv6, each can be turned off independently
- Several detection services tried in rotating order so one broken or rate-limited service does not block detection
- A detected change is confirmed against a second source before you are notified

Dynamic DNS
- Cloudflare (API token), DuckDNS, AWS Route53, and any dyndns2-compatible provider
- Failed updates are retried on the next check

Observability
- HTTP status API: `/healthz`, `/api/status` (JSON), and Prometheus `/metrics`
- MQTT publishing with Home Assistant auto-discovery
- Optional geographic data (city, region, country, ISP, timezone) via ipinfo.io

Events
- Notice on startup, optional heartbeat, and internet outage detection with a recovery notification

Operations
- Graceful shutdown on SIGTERM, atomic state file writes with a change history
- Retry with exponential backoff for notifications
- Runs as a non-root user (uid 1000)
- Multi-architecture image (AMD64 and ARM64)

---

## Supported architectures

| Architecture | Tags | Status |
|--------------|------|--------|
| x86-64 (AMD64) | `latest`, `2.5.0` | Supported |
| ARM64 (aarch64) | `latest`, `2.5.0` | Supported |

Docker pulls the correct image for your platform automatically. ARM64 covers
Raspberry Pi 4 and newer, Apple Silicon, and AWS Graviton.

---

## Quick start

Create the host directories and make them writable by uid 1000:

```bash
mkdir -p data logs
sudo chown -R 1000:1000 data logs
```

### docker run (Discord)

```bash
docker run -d \
  --name wanwatcher \
  --restart unless-stopped \
  -e DISCORD_ENABLED="true" \
  -e DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN" \
  -e SERVER_NAME="My Server" \
  -v ./data:/data \
  -v ./logs:/logs \
  noxied/wanwatcher:2.5.0
```

### docker compose

```yaml
services:
  wanwatcher:
    image: noxied/wanwatcher:2.5.0
    container_name: wanwatcher
    restart: unless-stopped
    environment:
      SERVER_NAME: "My Server"
      CHECK_INTERVAL: "900"
      DISCORD_ENABLED: "true"
      DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
    volumes:
      - ./data:/data
      - ./logs:/logs
```

```bash
docker compose up -d
```

---

## Configuration

Everything is set through environment variables. Booleans are the string
`"true"` (anything else is false). Lists are comma separated. At least one
notification method must be enabled.

### Discord

```yaml
DISCORD_ENABLED: "true"
DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
DISCORD_AVATAR_URL: ""   # optional; the webhook's own avatar is used when empty
```

### Telegram

```yaml
TELEGRAM_ENABLED: "true"
TELEGRAM_BOT_TOKEN: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID: "123456789"
TELEGRAM_PARSE_MODE: "HTML"
```

### Email (SMTP)

```yaml
EMAIL_ENABLED: "true"
EMAIL_SMTP_HOST: "smtp.gmail.com"
EMAIL_SMTP_PORT: "587"          # 587 for TLS, 465 for SSL
EMAIL_SMTP_USER: "you@gmail.com"
EMAIL_SMTP_PASSWORD: "app-password"
EMAIL_FROM: "wanwatcher@example.com"
EMAIL_TO: "admin@example.com"   # comma separated for multiple recipients
EMAIL_USE_TLS: "true"
```

### Apprise

One setting opens 100+ services. See the
[Apprise URL list](https://github.com/caronc/apprise#supported-notifications).

```yaml
APPRISE_ENABLED: "true"
APPRISE_URLS: "ntfy://ntfy.sh/my-topic,pover://user@token"
```

### Dynamic DNS

```yaml
DDNS_ENABLED: "true"
DDNS_PROVIDER: "cloudflare"     # cloudflare | duckdns | dyndns2 | route53

# Cloudflare
CLOUDFLARE_API_TOKEN: "token-with-zone-dns-edit"
CLOUDFLARE_ZONE: "example.com"
CLOUDFLARE_RECORDS: "home.example.com,vpn.example.com"
CLOUDFLARE_PROXIED: "false"

# DuckDNS
DUCKDNS_TOKEN: "your-token"
DUCKDNS_DOMAINS: "mysub"

# dyndns2 (No-IP, Dynu, and compatibles)
DYNDNS2_SERVER: "https://dynupdate.no-ip.com"
DYNDNS2_USERNAME: "user"
DYNDNS2_PASSWORD: "password"
DYNDNS2_HOSTNAMES: "host.example.com"

# AWS Route53 (creds need route53:ChangeResourceRecordSets on the zone)
ROUTE53_ACCESS_KEY_ID: "AKIA..."
ROUTE53_SECRET_ACCESS_KEY: "your-secret"
ROUTE53_HOSTED_ZONE_ID: "Z1234567890ABC"
ROUTE53_RECORDS: "home.example.com"
```

### Status API and MQTT

```yaml
API_ENABLED: "true"
API_PORT: "8080"                # publish this port to reach the API

MQTT_ENABLED: "true"
MQTT_HOST: "192.168.1.10"
MQTT_PORT: "1883"
MQTT_USERNAME: "wanwatcher"
MQTT_PASSWORD: "secret"
MQTT_HA_DISCOVERY: "true"       # sensors appear in Home Assistant automatically
```

### General and events

```yaml
CHECK_INTERVAL: "900"           # seconds between checks (minimum 60)
MONITOR_IPV4: "true"
MONITOR_IPV6: "true"
IP_CHANGE_CONFIRMATION: "true"  # confirm a change with a second source
IPINFO_TOKEN: ""                # optional ipinfo.io token for geo data

NOTIFY_ON_STARTUP: "true"
HEARTBEAT_ENABLED: "false"
HEARTBEAT_INTERVAL: "86400"
OUTAGE_DETECTION_ENABLED: "true"
OUTAGE_THRESHOLD: "3"

UPDATE_CHECK_ENABLED: "true"
UPDATE_CHECK_INTERVAL: "86400"
```

The full reference with every variable and default is in the
[README](https://github.com/noxied/wanwatcher#configuration).

---

## Volumes and ports

| Mount | Purpose |
|-------|---------|
| `/data` | State file with the current IPs and change history (persistent) |
| `/logs` | Application logs |

Port 8080 only needs publishing when `API_ENABLED=true`.

---

## Health check

The image ships a healthcheck. With the status API enabled it queries
`/healthz`; otherwise it confirms the state file is valid JSON and was
refreshed within the expected interval, so a stuck loop is reported as
unhealthy.

```bash
docker inspect --format='{{json .State.Health}}' wanwatcher
```

---

## Monitoring and logs

View logs:

```bash
docker logs -f wanwatcher
```

Read the current state:

```bash
docker exec wanwatcher cat /data/ipinfo.db
```

With `API_ENABLED=true`, query the status and metrics:

```bash
curl http://localhost:8080/api/status
curl http://localhost:8080/metrics
```

---

## Updating

docker compose:

```bash
docker compose pull
docker compose up -d
```

docker run:

```bash
docker pull noxied/wanwatcher:latest
docker stop wanwatcher && docker rm wanwatcher
# re-run your docker run command
```

See the [upgrade guide](https://github.com/noxied/wanwatcher/blob/main/UPGRADING.md)
for version-specific notes, including the uid 1000 change in 2.0.

---

## Troubleshooting

Container exits immediately
- Usually a configuration error. Check `docker logs wanwatcher` for the validation output. Common causes: no notification method enabled, an invalid webhook URL, or a missing required variable.

Permission denied on /data or /logs after upgrading to 2.0
- The container runs as uid 1000. Run `sudo chown -R 1000:1000 ./data ./logs` on the host directories.

Notifications not sending
- Failed sends are retried three times with backoff. Check `docker logs wanwatcher | grep -i "notification\|retry"` and verify credentials.

IPv6 not detected
- Confirm the host has IPv6 connectivity and that `MONITOR_IPV6="true"`.

More help: [troubleshooting guide](https://github.com/noxied/wanwatcher/blob/main/docs/TROUBLESHOOTING.md).

---

## Building from source

AMD64:

```bash
docker build -t wanwatcher:local .
```

Multi-arch (requires buildx):

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t wanwatcher:local \
  --push .
```

---

## Tags

| Tag | Meaning |
|-----|---------|
| `2.5.0` | This exact release |
| `2.0` | Latest 2.0.x patch |
| `2` | Latest 2.x release |
| `latest` | Latest stable release |

---

## Version history

| Version | Date | Highlights |
|---------|------|------------|
| 2.5.0 | 2026-06-13 | Reliability hardening (/healthz staleness, isolated side-effect failures) |
| 2.4.1 | 2026-06-13 | Security: escape untrusted strings in notifications |
| 2.3.0 | 2026-06-13 | AWS Route53 DDNS provider |
| 2.2.0 | 2026-06-13 | Secrets from files, Trivy/SBOM/Cosign supply-chain security |
| 2.1.0 | 2026-06-13 | Optional JSON logging (LOG_FORMAT), adaptive backoff with jitter |
| 2.0.0 | 2026-06-11 | Package rewrite, Apprise, multi-source detection, DDNS, status API and metrics, MQTT and Home Assistant, events, non-root container |
| 1.4.1 | 2025-11-02 | Python 3.14, code quality and security fixes, smaller image |
| 1.4.0 | 2025-11-02 | Configuration validation, notification retry, expanded tests |
| 1.3.0 | 2025-10-27 | Email notifications, update checking, custom avatars |
| 1.2.0 | 2025-10-27 | Telegram support, IPv6 monitoring |

[Full changelog](https://github.com/noxied/wanwatcher/blob/main/CHANGELOG.md)

---

## Documentation

- [README](https://github.com/noxied/wanwatcher/blob/main/README.md)
- [Changelog](https://github.com/noxied/wanwatcher/blob/main/CHANGELOG.md)
- [Upgrade guide](https://github.com/noxied/wanwatcher/blob/main/UPGRADING.md)
- [Troubleshooting](https://github.com/noxied/wanwatcher/blob/main/docs/TROUBLESHOOTING.md)
- [Security policy](https://github.com/noxied/wanwatcher/blob/main/SECURITY.md)
- [Contributing](https://github.com/noxied/wanwatcher/blob/main/CONTRIBUTING.md)

---

## Security

- Keep tokens, webhook URLs, and passwords in environment variables, not in images
- Secrets are never written to the logs
- Report security issues through the policy linked above

---

## Links

- GitHub: https://github.com/noxied/wanwatcher
- Issues: https://github.com/noxied/wanwatcher/issues
- Discussions: https://github.com/noxied/wanwatcher/discussions

MIT licensed.
