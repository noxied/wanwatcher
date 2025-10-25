FROM python:3.11-slim

# Set metadata
LABEL maintainer="WANwatcher"
LABEL description="WAN IP Monitoring with Discord Notifications"
LABEL version="1.0"

# Set working directory
WORKDIR /app

# Install dependencies
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
    CHECK_INTERVAL="900"

# Copy ipinfo module (lightweight implementation)
COPY ipinfo.py /usr/local/lib/python3.11/site-packages/ipinfo.py

# Set script as executable
RUN chmod +x /app/wanwatcher.py

# Health check
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import os; exit(0 if os.path.exists('/data/ipinfo.db') else 1)"

# Run the application in loop mode
CMD ["python3", "-u", "/app/wanwatcher_docker.py"]
