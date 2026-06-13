# Upgrading WANwatcher

Version-specific upgrade notes. The newest upgrade path is at the top.

## 2.3.x to 2.4.0

No breaking changes and nothing to configure. The application image is
functionally identical to 2.3.0; this release adds repository and supply-chain
tooling (OpenSSF Scorecard, SBOM attached to releases). Pull the new image if
you want the matching version label, otherwise no action is needed.

## 2.2.x to 2.3.0

No breaking changes and no required configuration. Pull the new image and
restart:

```bash
docker compose pull
docker compose up -d
```

What changed:

- New AWS Route53 DDNS provider. Set `DDNS_PROVIDER=route53` with the
  `ROUTE53_*` variables to update Route53 records on IP changes. Existing
  providers and configuration are untouched; this is opt-in.

## 2.1.x to 2.2.0

No breaking changes and no required configuration. Pull the new image and
restart:

```bash
docker compose pull
docker compose up -d
```

What changed:

- Secrets can now be supplied from files with the `<NAME>_FILE` convention, for
  Docker and Kubernetes secret mounts. Existing plain variables keep working
  unchanged; this is opt-in. Note the fail-fast behaviour: if you set a
  `_FILE` variable to a path that does not exist, the container stops at
  startup with a clear error instead of running without the secret.
- Published images are now signed with Cosign and ship with an SBOM. Existing
  deployments need no change; see SECURITY.md if you want to verify the
  signature before pulling.

## 2.0.x to 2.1.0

No breaking changes and no required configuration. Pull the new image and
restart:

```bash
docker compose pull
docker compose up -d
```

What changed:

- Optional structured JSON logging. Set `LOG_FORMAT=json` to emit one JSON
  object per line (UTC timestamps) for log aggregators; the default stays
  human-readable text, so doing nothing keeps the old behaviour.
- After a failed check the monitor retries sooner (short adaptive backoff
  capped at `CHECK_INTERVAL`) and adds jitter to retry delays. This is
  automatic; there is nothing to configure.

## 1.x to 2.0.0

v2.0.0 restructures the application into a Python package and adds a number
of opt-in features. Your existing configuration keeps working, but there is
one breaking change you have to handle before starting the new image.

### What breaks

1. The container now runs as a non-root user (uid 1000). Host directories
   mounted on `/data` and `/logs` must be writable by that user, otherwise
   the container fails at startup with permission errors. Fix it once before
   upgrading:

   ```bash
   sudo chown -R 1000:1000 ./data ./logs
   ```

   Adjust the paths to wherever your volumes live. On NAS systems
   (Synology, TrueNAS, Unraid), set the owner of the shared folders to
   uid/gid 1000 through the UI or shell.

2. The legacy standalone script `wanwatcher.py` was removed. If you were
   running it from cron instead of using Docker, switch to the container.

3. The image command changed from running a script to `python -m wanwatcher`.
   This only matters if you override the CMD in your compose file or run
   command; if you do, update it.

### What migrates automatically

- All v1 environment variables work unchanged. Nothing to rename.
- The state file is migrated on first read, including the old plain-text
  format and the `update_notified.txt` sidecar file.

### Upgrade steps

```bash
# 1. Fix volume ownership (the breaking part)
sudo chown -R 1000:1000 ./data ./logs

# 2. Point your compose file at the new image
#    image: noxied/wanwatcher:2.0.0

# 3. Pull and restart
docker compose pull
docker compose up -d

# 4. Check the logs
docker compose logs -f wanwatcher
```

You should see the version banner and, with `NOTIFY_ON_STARTUP` left at its
default, a startup message on your notification channels.

### New opt-in features

Nothing below is enabled by default (except the startup notice and outage
detection); turn on what you need:

- Apprise notifications for 100+ services: `APPRISE_ENABLED`, `APPRISE_URLS`
- Dynamic DNS updates: `DDNS_ENABLED`, `DDNS_PROVIDER` (cloudflare, duckdns,
  or dyndns2) plus the provider's variables
- HTTP status API with Prometheus metrics: `API_ENABLED`, `API_PORT`
  (publish the port, e.g. `-p 8080:8080`)
- MQTT with Home Assistant discovery: `MQTT_ENABLED`, `MQTT_HOST`, and
  friends
- Heartbeat messages: `HEARTBEAT_ENABLED`, `HEARTBEAT_INTERVAL`

See the [README](README.md) for the full variable reference.

### Rollback

If something goes wrong, point the image back at `noxied/wanwatcher:1.4.1`
and start it again. The migrated state file remains readable by v1 (it is a
superset of the v1 JSON format). The chown does not need to be undone; v1
ran as root and does not care about ownership.

## 1.3.x to 1.4.x

No breaking changes and no new required configuration. Pull the new image
and restart:

```bash
docker compose pull
docker compose down
docker compose up -d
```

What changed in 1.4.x:

- Configuration is validated at startup. An invalid configuration now stops
  the container with an explanation instead of failing silently. If the
  container exits right after starting, read the logs.
- Failed notifications are retried up to 3 times with exponential backoff.
- IPv6 validation filters out loopback, link-local, multicast, private, and
  reserved addresses.
- 1.4.1 moved the image to Python 3.14.

Verify after upgrading:

```bash
docker logs wanwatcher | grep "WANwatcher v"
docker logs wanwatcher | grep -i validation
```

## 1.3.1 to 1.3.2

Patch release. If you configured email by copying the README examples from
1.3.1 or earlier, the variable names in those examples were wrong and must
be corrected:

```yaml
# wrong (from the old README)   # correct
EMAIL_SMTP_SERVER:         ->   EMAIL_SMTP_HOST:
EMAIL_USERNAME:            ->   EMAIL_SMTP_USER:
EMAIL_PASSWORD:            ->   EMAIL_SMTP_PASSWORD:
```

The code always expected the correct names; only the documentation was
wrong. After fixing the names, pull and restart as usual.

1.3.3 is the same code with corrected version numbers.

## 1.3.0 to 1.3.1

1.3.1 added the `DISCORD_ENABLED` flag. If you use Discord, add it:

```yaml
environment:
  DISCORD_ENABLED: "true"
  DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/..."
```

Without it, Discord notifications stay off. The avatar handling also
changed: by default the webhook's configured avatar (set in Discord) is
used, and `DISCORD_AVATAR_URL` overrides it with a custom image URL.

## 1.2.0 to 1.3.0

No breaking changes. New optional features:

- Email notifications: `EMAIL_ENABLED`, `EMAIL_SMTP_HOST`,
  `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASSWORD`,
  `EMAIL_FROM`, `EMAIL_TO`, `EMAIL_USE_TLS`, `EMAIL_SUBJECT_PREFIX`.
  Gmail users need an [app password](https://support.google.com/accounts/answer/185833).
- Update checking: `UPDATE_CHECK_ENABLED`, `UPDATE_CHECK_INTERVAL`,
  `UPDATE_CHECK_ON_STARTUP`.

## 1.1.0 and earlier to 1.2.0

No breaking changes. New optional features:

- Telegram notifications: `TELEGRAM_ENABLED`, `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`, `TELEGRAM_PARSE_MODE`. Create the bot with
  [@BotFather](https://t.me/BotFather) and get your chat id from
  [@userinfobot](https://t.me/userinfobot).
- IPv6 monitoring: `MONITOR_IPV4`, `MONITOR_IPV6` (both default to true).

## Before any upgrade

Back up your state and configuration first:

```bash
cp -r data data.backup
cp docker-compose.yml docker-compose.yml.backup
```

To roll back, restore the backup, set the previous image tag, and
`docker compose up -d` again.

## Testing after an upgrade

```bash
# logs should show the new version and no errors
docker compose logs --tail 50 wanwatcher

# force a "first run" notification to test delivery
docker compose down
sudo rm -f data/ipinfo.db
docker compose up -d
```

If you run into problems, check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
or open an issue at https://github.com/noxied/wanwatcher/issues.
