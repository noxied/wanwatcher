FROM python:3.14-slim

# Set metadata
LABEL maintainer="noxied"
LABEL description="WAN IP Monitoring with Multi-Platform Notifications (Discord, Telegram, Email) - IPv4 & IPv6 Support"
LABEL version="1.4.1"
LABEL org.opencontainers.image.title="WANwatcher"
LABEL org.opencontainers.image.description="Monitor WAN IPv4/IPv6 addresses with Discord, Telegram, and Email notifications"
LABEL org.opencontainers.image.version="1.4.1"
LABEL org.opencontainers.image.authors="noxied"
LABEL org.opencontainers.image.url="https://github.com/noxied/wanwatcher"
LABEL org.opencontainers.image.source="https://github.com/noxied/wanwatcher"
LABEL org.opencontainers.image.licenses="MIT"

# Set working directory
WORKDIR /app

# Install dependencies
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir requests ipinfo

# Copy application files
COPY wanwatcher_docker.py /app/
COPY notifications.py /app/
COPY config_validator.py /app/

# Copy avatar image for webhook notifications
COPY wan_watcher.png /app/avatar.png

# Create directories for data persistence
RUN mkdir -p /data /logs

# Set environment variables with defaults
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
    UPDATE_CHECK_ENABLED="true" \
    UPDATE_CHECK_INTERVAL="86400" \
    UPDATE_CHECK_ON_STARTUP="true" \
    IPINFO_TOKEN="" \
    SERVER_NAME="WANwatcher Docker" \
    IP_DB_FILE="/data/ipinfo.db" \
    LOG_FILE="/logs/wanwatcher.log" \
    BOT_NAME="WANwatcher" \
    CHECK_INTERVAL="900" \
    MONITOR_IPV4="true" \
    MONITOR_IPV6="true"

# Set script as executable
RUN chmod +x /app/wanwatcher_docker.py

# Health check - verifies the database file exists
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import os; exit(0 if os.path.exists('/data/ipinfo.db') else 1)"

# Run the application in continuous loop mode
CMD ["python3", "-u", "/app/wanwatcher_docker.py"]
