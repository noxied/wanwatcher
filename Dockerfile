FROM python:3.14-slim

LABEL maintainer="noxied"
LABEL description="WAN IP monitoring with notifications, DDNS updates and Home Assistant integration"
LABEL version="2.4.1"
LABEL org.opencontainers.image.title="WANwatcher"
LABEL org.opencontainers.image.description="Monitor WAN IPv4/IPv6 addresses with notifications, DDNS and MQTT"
LABEL org.opencontainers.image.version="2.4.1"
LABEL org.opencontainers.image.authors="noxied"
LABEL org.opencontainers.image.url="https://github.com/noxied/wanwatcher"
LABEL org.opencontainers.image.source="https://github.com/noxied/wanwatcher"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY wanwatcher/ /app/wanwatcher/
COPY scripts/healthcheck.py /app/healthcheck.py
COPY wan_watcher.png /app/avatar.png

# Run as a dedicated non-root user. Volumes mounted on /data and /logs must
# be writable by uid 1000 (see UPGRADING.md when coming from 1.x).
RUN useradd --create-home --uid 1000 wanwatcher \
    && mkdir -p /data /logs \
    && chown -R wanwatcher:wanwatcher /data /logs /app

ENV DISCORD_ENABLED="false" \
    DISCORD_WEBHOOK_URL="" \
    DISCORD_AVATAR_URL="" \
    TELEGRAM_ENABLED="false" \
    TELEGRAM_BOT_TOKEN="" \
    TELEGRAM_CHAT_ID="" \
    TELEGRAM_PARSE_MODE="HTML" \
    EMAIL_ENABLED="false" \
    EMAIL_SMTP_HOST="" \
    EMAIL_SMTP_PORT="587" \
    EMAIL_SMTP_USER="" \
    EMAIL_SMTP_PASSWORD="" \
    EMAIL_FROM="" \
    EMAIL_TO="" \
    EMAIL_USE_TLS="true" \
    EMAIL_USE_SSL="false" \
    EMAIL_SUBJECT_PREFIX="[WANwatcher]" \
    APPRISE_ENABLED="false" \
    APPRISE_URLS="" \
    DDNS_ENABLED="false" \
    DDNS_PROVIDER="" \
    CLOUDFLARE_API_TOKEN="" \
    CLOUDFLARE_ZONE="" \
    CLOUDFLARE_RECORDS="" \
    CLOUDFLARE_PROXIED="false" \
    CLOUDFLARE_TTL="1" \
    DUCKDNS_TOKEN="" \
    DUCKDNS_DOMAINS="" \
    DYNDNS2_SERVER="" \
    DYNDNS2_USERNAME="" \
    DYNDNS2_PASSWORD="" \
    DYNDNS2_HOSTNAMES="" \
    ROUTE53_ACCESS_KEY_ID="" \
    ROUTE53_SECRET_ACCESS_KEY="" \
    ROUTE53_HOSTED_ZONE_ID="" \
    ROUTE53_RECORDS="" \
    ROUTE53_TTL="300" \
    API_ENABLED="false" \
    API_BIND="0.0.0.0" \
    API_PORT="8080" \
    MQTT_ENABLED="false" \
    MQTT_HOST="" \
    MQTT_PORT="1883" \
    MQTT_USERNAME="" \
    MQTT_PASSWORD="" \
    MQTT_CLIENT_ID="wanwatcher" \
    MQTT_TOPIC_PREFIX="wanwatcher" \
    MQTT_TLS="false" \
    MQTT_HA_DISCOVERY="true" \
    MQTT_HA_DISCOVERY_PREFIX="homeassistant" \
    NOTIFY_ON_STARTUP="true" \
    HEARTBEAT_ENABLED="false" \
    HEARTBEAT_INTERVAL="86400" \
    OUTAGE_DETECTION_ENABLED="true" \
    OUTAGE_THRESHOLD="3" \
    UPDATE_CHECK_ENABLED="true" \
    UPDATE_CHECK_INTERVAL="86400" \
    UPDATE_CHECK_ON_STARTUP="true" \
    IPINFO_TOKEN="" \
    SERVER_NAME="WANwatcher Docker" \
    IP_DB_FILE="/data/ipinfo.db" \
    LOG_FILE="/logs/wanwatcher.log" \
    LOG_FORMAT="text" \
    BOT_NAME="WANwatcher" \
    CHECK_INTERVAL="900" \
    HTTP_TIMEOUT="10" \
    IP_CHANGE_CONFIRMATION="true" \
    MONITOR_IPV4="true" \
    MONITOR_IPV6="true"

USER wanwatcher

# Status API port (only used when API_ENABLED=true)
EXPOSE 8080

HEALTHCHECK --interval=5m --timeout=10s --start-period=60s --retries=3 \
    CMD ["python3", "/app/healthcheck.py"]

CMD ["python3", "-u", "-m", "wanwatcher"]
