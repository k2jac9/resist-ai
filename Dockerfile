FROM python:3.12-slim

WORKDIR /app

# System deps: build toolchain for wheels, curl for healthchecks, and the
# native pango/cairo/gdk-pixbuf libraries weasyprint needs for PDF export.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

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
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

# Expose ports
EXPOSE 7860 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
