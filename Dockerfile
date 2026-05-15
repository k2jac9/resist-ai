FROM python:3.13-slim

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
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# Create unprivileged user and hand over /app
RUN groupadd --system --gid 1000 resistai \
    && useradd --system --uid 1000 --gid resistai --home /app --shell /usr/sbin/nologin resistai \
    && chown -R resistai:resistai /app
USER resistai

# Expose ports
EXPOSE 7860 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
