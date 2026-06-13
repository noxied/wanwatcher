# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 2.0.x   | Yes |
| 1.4.x   | Security fixes only |
| < 1.4   | No |

## What the 2.x image does for you

- The container runs as a dedicated non-root user (uid 1000).
- Dependencies are pinned in `requirements.txt` and scanned in CI (Bandit,
  Safety, Dependabot), and the built image is scanned with Trivy before it can
  be published.
- Published images are signed with Cosign (keyless, via Sigstore) and ship with
  a CycloneDX SBOM, so you can verify provenance and inspect the contents.
- Secrets (webhook URLs, bot tokens, SMTP and MQTT passwords, Apprise URLs)
  are never written to logs; only redacted forms appear.
- Every sensitive value can be supplied from a file via the `<NAME>_FILE`
  convention, for native Docker and Kubernetes secret mounts.
- The Telegram bot token is not embedded in stored URLs.
- No inbound ports are required. The status API is off by default; when you
  enable it, you decide what to publish.

## Never commit secrets

Do not commit any of these to version control:

- Discord webhook URLs
- Telegram bot tokens and chat ids
- SMTP passwords
- Apprise URLs (they usually embed credentials)
- Cloudflare API tokens, DuckDNS tokens, dyndns2 passwords
- MQTT passwords
- ipinfo.io tokens

Safe ways to pass them instead:

Environment variables:

```bash
export DISCORD_WEBHOOK_URL="your_webhook"
docker run -e DISCORD_WEBHOOK_URL ... noxied/wanwatcher:2.5.0
```

A `.env` file (add it to `.gitignore`):

```bash
docker compose --env-file .env up -d
```

With variable substitution in the compose file:

```yaml
environment:
  DISCORD_WEBHOOK_URL: "${DISCORD_WEBHOOK_URL}"
```

Docker secrets, or the secret management built into Portainer or Kubernetes,
also work. The cleanest option is the `<NAME>_FILE` convention: point, for
example, `DISCORD_WEBHOOK_URL_FILE` at a mounted secret file and the value is
read from there, never appearing in the environment or the compose file. What
you should not do is paste real tokens into a compose file that lives in a git
repository, or bake them into a Dockerfile with `ENV`.

## Verifying an image

Published images are signed with Cosign using keyless signing. You can verify
that an image came from this repository's CI before running it:

```bash
cosign verify noxied/wanwatcher:2.5.0 \
  --certificate-identity-regexp "https://github.com/noxied/wanwatcher/.*" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Network exposure

WANwatcher only makes outbound HTTPS requests: to the IP detection services,
to the notification APIs you enable (Discord, Telegram, your SMTP server,
Apprise targets), to your DDNS provider, and to ipinfo.io and the GitHub API
if configured. MQTT is an outbound TCP connection to your broker.

The only listening service is the optional status API (`API_ENABLED`,
default off). It has no authentication, so do not publish it to the
internet; keep it on an internal Docker network or bind it to localhost and
let your monitoring stack scrape it from there.

## Token hygiene

- A Discord webhook URL is a credential: anyone who has it can post to your
  channel. Regenerate it if it leaks.
- A Telegram bot token gives full control of the bot. Revoke and reissue
  via @BotFather if compromised.
- Use an app-specific password for SMTP, not your account password.
- Give Cloudflare tokens the minimum scope (Zone.DNS edit on one zone).
- Rotate tokens periodically and after any suspected exposure.

## Container hardening

Reasonable extras for the paranoid:

```yaml
services:
  wanwatcher:
    image: noxied/wanwatcher:2.5.0   # pin a version, avoid :latest
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 128M
```

The state file (`/data/ipinfo.db`) and the logs contain your public IP
addresses and change history. Not secret, but they reveal your location and
ISP, so do not expose those directories publicly.

## Reporting a vulnerability

Do not open a public issue. Email
[240063414+noxied@users.noreply.github.com](mailto:240063414+noxied@users.noreply.github.com)
with a description, steps to reproduce, and the impact as you understand it.

You can expect an acknowledgment within 48 hours and an initial assessment
within a week. Fix timelines depend on severity; critical issues are
addressed as fast as possible, low-severity ones in the next release.

For non-security problems, see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
and the [configuration reference](README.md#configuration).
