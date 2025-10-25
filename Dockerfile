FROM python:3.11-slim

# Set metadata
LABEL maintainer="noxied"
LABEL description="WAN IP Monitoring with Discord Notifications - IPv4 & IPv6 Support"
LABEL version="1.1.0"
LABEL org.opencontainers.image.title="WANwatcher"
LABEL org.opencontainers.image.description="Monitor WAN IPv4/IPv6 addresses with Discord notifications"
LABEL org.opencontainers.image.version="1.1.0"
LABEL org.opencontainers.image.authors="noxied"
LABEL org.opencontainers.image.url="https://github.com/noxied/wanwatcher"
LABEL org.opencontainers.image.source="https://github.com/noxied/wanwatcher"
LABEL org.opencontainers.image.licenses="MIT"

# Set working directory
WORKDIR /app

# Install dependencies
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir requests

# Copy application files
COPY wanwatcher*.py /app/

# Create directories for data persistence
RUN mkdir -p /data /logs

# Set environment variables with defaults
ENV DISCORD_WEBHOOK_URL="" \
    IPINFO_TOKEN="" \
    SERVER_NAME="WANwatcher Docker" \
    IP_DB_FILE="/data/ipinfo.db" \
    LOG_FILE="/logs/wanwatcher.log" \
    BOT_NAME="WANwatcher" \
    CHECK_INTERVAL="900" \
    MONITOR_IPV4="true" \
    MONITOR_IPV6="true"

# Copy ipinfo module (lightweight implementation)
COPY ipinfo.py /usr/local/lib/python3.11/site-packages/ipinfo.py

# Set script as executable
RUN chmod +x /app/wanwatcher.py /app/wanwatcher_docker.py

# Health check - verifies the database file exists
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import os; exit(0 if os.path.exists('/data/ipinfo.db') else 1)"

# Run the application in continuous loop mode
CMD ["python3", "-u", "/app/wanwatcher_docker.py"]
