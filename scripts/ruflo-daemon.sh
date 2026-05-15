#!/usr/bin/env bash
set -euo pipefail

PID_FILE=".claude-flow/daemon.pid"

if [[ -f "$PID_FILE" ]]; then
    PID=$(tr -d '[:space:]' < "$PID_FILE")
    if [[ -n "$PID" ]] && ! kill -0 "$PID" 2>/dev/null; then
        echo "[ruflo-daemon] Removing stale PID file (pid=$PID not running)"
        rm -f "$PID_FILE"
    fi
fi

exec ruflo daemon "${1:-start}" "${@:2}"
