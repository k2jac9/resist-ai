#!/bin/bash
set -e

SERVICE="${1:-${SERVICE:-web}}"

case "$SERVICE" in
  web)
    echo "Starting Gradio web UI on port 7860..."
    exec python3 -m src.app
    ;;
  api)
    echo "Starting FastAPI server on port 8000..."
    exec uvicorn src.api:app --host 0.0.0.0 --port 8000
    ;;
  *)
    echo "Unknown service: $SERVICE"
    echo "Usage: docker-entrypoint.sh [web|api]"
    exit 1
    ;;
esac
