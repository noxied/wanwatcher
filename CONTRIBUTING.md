# Contributing to WANwatcher

Bug reports, fixes, and new providers are welcome. This document covers the
practical parts: setting up a dev environment, running the checks, and where
new code goes.

## Development setup

```bash
git clone https://github.com/YOUR_USERNAME/wanwatcher.git
cd wanwatcher

python3 -m venv venv
source venv/bin/activate    # on Windows: venv\Scripts\activate

pip install -r requirements-dev.txt
```

This installs the runtime dependencies (`requests`, `apprise`, `paho-mqtt`)
plus pytest, the linters, and type stubs.

Run the app locally with `python -m wanwatcher` (it reads its configuration
from environment variables; set `IP_DB_FILE` and `LOG_FILE` to writable
paths when not running in Docker).

To test the Docker image:

```bash
docker build -t wanwatcher:dev .
docker run --rm \
  -e DISCORD_ENABLED="true" \
  -e DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." \
  -v ./data:/data -v ./logs:/logs \
  wanwatcher:dev
```

Remember the image runs as uid 1000, so `./data` and `./logs` must be
writable by that user.

## Tests

```bash
pytest tests/ -v
pytest tests/ --cov --cov-report=term
```

CI runs the suite on Python 3.10 through 3.14, so avoid syntax or stdlib
features newer than 3.10. Mock all network calls (`requests`, `smtplib`,
MQTT); tests must pass offline. Patch `time.sleep` when testing retry logic
so the suite stays fast.

## Linting and formatting

CI enforces these, so run them before pushing:

```bash
black wanwatcher/ tests/
isort wanwatcher/ tests/
flake8 wanwatcher/ --count --select=E9,F63,F7,F82 --show-source --statistics
mypy wanwatcher/ --ignore-missing-imports
```

isort is configured with the Black profile in `pyproject.toml`. New functions
should have type annotations. Use the `logging` module, never `print()`, and
never log secrets (webhook URLs, tokens, passwords); see
`wanwatcher/config.py:redact()` and the redaction helpers in
`wanwatcher/notifiers/__init__.py`.

## Package layout

```
wanwatcher/
  __main__.py      entry point (python -m wanwatcher)
  app.py           main loop, events, signal handling
  config.py        all env vars and defaults (single source of truth)
  validation.py    startup configuration validation
  detector.py      IP detection sources and rotation
  state.py         JSON state file, atomic writes, migration
  api.py           HTTP status API and /metrics
  metrics.py       Prometheus metric registry
  mqtt.py          MQTT publisher and HA discovery
  geo.py           ipinfo.io lookup
  updates.py       GitHub release check
  notifiers/       notification providers
  ddns/            DDNS clients
```

## Adding a notification provider

1. Create `wanwatcher/notifiers/yourservice.py` with a class extending
   `NotificationProvider` from `wanwatcher/notifiers/base.py`. Implement
   `send_notification()` and `send_update_notification()`; override
   `send_event()` if the service has a natural representation for generic
   messages (startup, heartbeat, outage).
2. Add a config dataclass with a `from_env()` classmethod in
   `wanwatcher/config.py` and wire it into `Config`.
3. Register the provider in `build_manager()` in
   `wanwatcher/notifiers/__init__.py`.
4. Add validation in `wanwatcher/validation.py` (a `validate_yourservice()`
   method called from `validate_all()`).
5. Add the new env vars to the Dockerfile `ENV` block and to
   `docker-compose.yml` with comments.
6. Add tests in `tests/`, covering success, failure, and the retry path.
7. Document the variables in README.md.

Before writing a dedicated provider, check whether
[Apprise](https://github.com/caronc/apprise) already covers the service; if
it does, a documentation example may be all that is needed.

## Adding a DDNS provider

1. Create `wanwatcher/ddns/yourprovider.py` with a class extending
   `DDNSClient` from `wanwatcher/ddns/base.py`. Implement
   `_apply(ipv4, ipv6)` returning a mapping of record name to success flag,
   and call `_mark_failure(family)` for each address family a failed update
   affects (this is what makes the base class retry it on the next check).
2. Add a config dataclass in `wanwatcher/config.py` and hook it into
   `DDNSConfig`.
3. Register the provider in `build_ddns_client()` in
   `wanwatcher/ddns/__init__.py`.
4. Add validation, Dockerfile/compose entries, tests, and README docs as
   above.

The base class already handles change caching, retries, metrics, and error
containment; `_apply` only needs to talk to the provider's API.

## Pull requests

- Branch from `main` (`feature/...` or `fix/...`).
- Keep commits focused, one logical change each, with descriptive messages.
- Include tests for behavior changes and update the docs that the change
  touches (README, docker-compose.yml, CHANGELOG.md).
- Make sure `pytest`, `black --check`, `isort --check-only`, `flake8`, and
  `mypy` pass; CI runs all of them plus Bandit and Safety.
- Describe in the PR what the change does, why, and how you tested it.
- No secrets in code, tests, or fixtures.

## Reporting bugs

Check existing issues first, then open one with: what you expected, what
happened, steps to reproduce, logs (redact webhook URLs and tokens), and
your environment (image tag, platform, Docker version).

Security issues should not be reported publicly; see [SECURITY.md](SECURITY.md).

## License

By contributing you agree that your contributions are licensed under the
MIT License.
