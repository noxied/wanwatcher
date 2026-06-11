# Troubleshooting

Common problems and how to diagnose them. Almost everything starts with the
logs:

```bash
docker logs -f wanwatcher
# or, when mounted:
tail -f logs/wanwatcher.log
```

For the full list of environment variables and defaults, see the
[configuration reference](../README.md#configuration). If you are coming from
1.x, the [upgrade guide](../UPGRADING.md) covers the breaking change first.

## Volume permission errors after upgrading to 2.x

Since v2.0.0 the container runs as uid 1000 instead of root. If the host
directories mounted on `/data` and `/logs` are owned by root (which they
will be if a 1.x container created them), the container exits at startup
with errors like:

```
PermissionError: [Errno 13] Permission denied: '/data/ipinfo.db'
```

Fix the ownership once:

```bash
docker compose down
sudo chown -R 1000:1000 ./data ./logs
docker compose up -d
```

On Synology/TrueNAS/Unraid, set the owner of the mapped folders to uid/gid
1000 through the UI or a shell. If you cannot change ownership, making the
directories group- or world-writable also works, just less tidy.

## Container exits immediately

Check the logs first:

```bash
docker logs wanwatcher
```

Usual causes:

1. Configuration validation failed. The log says exactly which variable is
   the problem. Common cases: no notification method enabled at all, a
   webhook URL that is not HTTPS, `EMAIL_USE_TLS` and `EMAIL_USE_SSL` both
   set to true, a `DDNS_PROVIDER` without its required variables.
2. Volume permissions (see the section above).
3. Boolean values that are not exactly the string `"true"`. `True`, `1`,
   and `yes` all count as false.

## Container unhealthy

The healthcheck verifies that the state file exists, contains valid JSON,
and was refreshed recently. When `API_ENABLED=true`, it queries `/healthz`
instead.

```bash
docker inspect --format='{{json .State.Health}}' wanwatcher
```

Common causes:

- The container just started; give it one check interval.
- The state file cannot be written (permissions, full disk).
- Every IP check is failing, so the state file goes stale. Check the logs
  for source failures, and see "IP detection" below.

## Debugging with the status API

If you enable the API, it is the quickest way to see what the monitor
thinks is going on:

```yaml
environment:
  API_ENABLED: "true"
ports:
  - "8080:8080"
```

Then:

```bash
# health: status, last check time, uptime
curl http://localhost:8080/healthz

# full state: current IPs, last change, recent history
curl http://localhost:8080/api/status

# Prometheus metrics, including check failure counters
curl http://localhost:8080/metrics
```

`wanwatcher_check_failures_total` climbing while `wanwatcher_checks_total`
stays put means the detection sources are unreachable. If `/healthz` itself
does not answer, check that the port is published and that nothing else is
bound to it (the log line "Could not start status API" means the bind
failed).

## No notifications received

1. Confirm the platform is enabled and configured. The startup log lists
   every notifier that was registered, with warnings for ones that were
   enabled but missing settings.

2. Remember that an IP-change notification needs an IP change. To force a
   "first run" notification:

   ```bash
   docker compose down
   sudo rm -f data/ipinfo.db
   docker compose up -d
   ```

3. Test the channel directly:

   ```bash
   # Discord webhook
   curl -X POST -H "Content-Type: application/json" \
     -d '{"content":"Test"}' "YOUR_WEBHOOK_URL"

   # Telegram bot token
   curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getMe"
   ```

4. Failed sends are retried 3 times with backoff; the attempts show up in
   the logs:

   ```bash
   docker logs wanwatcher | grep -i "retry\|notification"
   ```

### Discord

- 404: the webhook was deleted or the URL is incomplete. Create a new one
  and copy the whole URL.
- 401: the token part at the end of the URL is missing or wrong.
- 429: rate limited. Increase `CHECK_INTERVAL` and do not point several
  instances at the same webhook.
- Avatar wrong or missing: set the avatar on the webhook in Discord, or
  point `DISCORD_AVATAR_URL` at a public image URL.

### Telegram

- Make sure you sent `/start` to your bot once; bots cannot message you
  first.
- For group chats the chat id is negative; copy it exactly.
- `getMe` failing means the token is wrong or was revoked.

### Email

Check the startup log for the email notifier line, then:

- Gmail needs an app password (2FA, then Google Account > Security > App
  passwords), not the account password.
- Port 587 goes with `EMAIL_USE_TLS=true`, port 465 with
  `EMAIL_USE_SSL=true`. Never both.
- Common hosts: `smtp.gmail.com:587`, `smtp-mail.outlook.com:587`,
  `smtp.mail.yahoo.com:587`.
- Multiple recipients go in `EMAIL_TO` comma separated.

### Apprise

- `APPRISE_URLS` is comma separated; a comma inside a single URL will split
  it. Check the startup log for how many URLs were loaded.
- Test a URL with the Apprise CLI:
  `pip install apprise && apprise -vv -b "test" "ntfy://host/topic"`.
- URL syntax per service is documented at
  https://github.com/caronc/apprise#supported-notifications

## DDNS records not updating

1. Verify DDNS is actually on: `DDNS_ENABLED=true` and a valid
   `DDNS_PROVIDER` (`cloudflare`, `duckdns`, or `dyndns2`). If the
   provider's required variables are missing, the startup log says so and
   DDNS stays disabled.

2. Watch the logs around an IP change:

   ```bash
   docker logs wanwatcher | grep -i ddns
   ```

   "no address changes since last successful update, skipping" is normal:
   updates only run when the detected IP differs from the last successfully
   applied one. Failed updates are retried on the next check.

3. Provider specifics:

   - Cloudflare: the token needs Zone.DNS edit permission for the zone in
     `CLOUDFLARE_ZONE`, and the records in `CLOUDFLARE_RECORDS` must already
     exist in that zone with matching types (A for IPv4, AAAA for IPv6).
   - DuckDNS: `DUCKDNS_DOMAINS` takes only the subdomain part (`myhome`,
     not `myhome.duckdns.org`).
   - dyndns2: `DYNDNS2_SERVER` must include the scheme
     (`https://dynupdate.no-ip.com`). Responses like `badauth` or `nohost`
     in the logs come straight from the provider and mean wrong credentials
     or an unknown hostname.

4. Remember DNS caching: verify with a direct query against an authoritative
   or public resolver, e.g. `dig home.example.com @1.1.1.1`.

## MQTT not connecting

1. Check the logs:

   ```bash
   docker logs wanwatcher | grep -i mqtt
   ```

   "connecting to host:port" followed by nothing means the broker is
   unreachable; "connection refused" with a reason code usually means bad
   credentials.

2. Things to verify:

   - `MQTT_HOST` is reachable from inside the container:
     `docker exec wanwatcher python3 -c "import socket; socket.create_connection(('BROKER',1883),5)"`.
     If the broker runs in another compose stack, use its service name and a
     shared network, not `localhost`.
   - Port 1883 for plain, 8883 with `MQTT_TLS=true`. `MQTT_TLS` only
     enables TLS; it does not change the port for you.
   - Username/password match an account on the broker, and the broker's ACL
     allows publishing under `MQTT_TOPIC_PREFIX` (default `wanwatcher`) and,
     for discovery, under `homeassistant/`.
   - Duplicate `MQTT_CLIENT_ID`s kick each other off the broker; give each
     instance its own id.

3. Watch the topics directly:

   ```bash
   mosquitto_sub -h BROKER -u USER -P PASS -t 'wanwatcher/#' -v
   ```

   You should see retained `ipv4`, `ipv6`, `last_change`, `state`, and
   `availability` messages. If Home Assistant shows no device, check that
   `MQTT_HA_DISCOVERY=true` (the default), that HA is connected to the same
   broker, and that `MQTT_HA_DISCOVERY_PREFIX` matches HA's discovery prefix
   (default `homeassistant`).

## IP detection failures

"Failed to retrieve IPv4 from all N sources" means none of the detection
services answered usably. The sources rotate, so a single dead service is
tolerated; all of them failing points at your network.

```bash
# connectivity and DNS from inside the container
docker exec wanwatcher python3 -c "import requests; print(requests.get('https://api.ipify.org?format=json', timeout=5).text)"
```

- Check the firewall allows outbound 443.
- If you are behind a proxy, pass `HTTP_PROXY`/`HTTPS_PROXY` to the
  container.
- For container DNS problems, set DNS servers in
  `/etc/docker/daemon.json` (`"dns": ["1.1.1.1", "8.8.8.8"]`) and restart
  Docker, or run the container with `--network host` to rule networking
  out.

IPv6 specifically: "no IPv6 detected" usually just means the host has no
global IPv6 connectivity, or the Docker network does not pass IPv6 through.
Test with `curl -6 https://api6.ipify.org` on the host; if that fails,
WANwatcher cannot do better. Set `MONITOR_IPV6=false` to silence the
warnings. Note that only globally routable addresses are accepted;
link-local, ULA (`fd00::/8`), loopback, and similar are filtered out by
design.

If checks fail repeatedly, outage detection (on by default) kicks in after
`OUTAGE_THRESHOLD` consecutive failures and sends an outage plus recovery
notification once connectivity returns.

## Geographic data missing

- `IPINFO_TOKEN` is optional; without it, notifications leave out the
  location data.
- With a token, verify it works:
  `curl -H "Authorization: Bearer YOUR_TOKEN" https://ipinfo.io/json`
- The free tier has a monthly request limit; check your usage on
  ipinfo.io. Lookups are only made when the IP changes, so normal usage
  stays far below it.

## Platform notes

TrueNAS Scale: make sure the restart policy is `unless-stopped` so the
container survives reboots, and remember the uid 1000 requirement when
creating datasets for `/data` and `/logs`.

Synology: create the shared folders in File Station first, give uid 1000
write access, and use absolute paths in Container Manager.

Raspberry Pi: the published image is multi-arch; `noxied/wanwatcher:2.0.0`
pulls the ARM64 variant automatically on a 64-bit OS. 32-bit ARM is not
published; build locally if you need it.

## Still stuck

Search the [existing issues](https://github.com/noxied/wanwatcher/issues), and
if nothing matches, open a new one with your logs (redact webhook URLs and
tokens), your configuration, what you already tried, and the platform you run
on. The [contributing guide](../CONTRIBUTING.md#reporting-bugs) has the details
of what to include.

For a suspected security vulnerability, do not open a public issue; follow the
[security policy](../SECURITY.md) instead.
