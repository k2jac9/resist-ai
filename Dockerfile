FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ src/
COPY config/ config/
COPY scripts/ scripts/

# Copy entrypoint
COPY config/docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run as a non-root user
RUN adduser --system --group --no-create-home app \
    && chown -R app:app /app
USER app

# Expose ports
EXPOSE 7860 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
