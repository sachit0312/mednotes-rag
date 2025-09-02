#!/usr/bin/env bash
# Restart local ngrok pointing to API port. Supports reserved domains.
# Usage:
#   bash scripts/restart_ngrok.sh
#   NGROK_DOMAIN=flea-whole-loosely.ngrok-free.app bash scripts/restart_ngrok.sh
#   PORT=8000 bash scripts/restart_ngrok.sh

set -euo pipefail

# Load repo deploy defaults if present
if [ -f "$(dirname "$0")/../deploy.env" ]; then
  # shellcheck disable=SC1091
  . "$(dirname "$0")/../deploy.env"
fi

PORT=${PORT:-8000}
NGROK_BIN=${NGROK_BIN:-ngrok}
NGROK_DOMAIN=${NGROK_DOMAIN:-}
LOG_FILE=${LOG_FILE:-ngrok.log}
PID_FILE=${PID_FILE:-ngrok.pid}

if ! command -v "$NGROK_BIN" >/dev/null 2>&1; then
  echo "ngrok not found. Install with: brew install ngrok" >&2
  exit 1
fi

echo "Stopping any existing ngrok..."
set +e
pkill -f "$NGROK_BIN http" 2>/dev/null
if [ -f "$PID_FILE" ]; then rm -f "$PID_FILE"; fi
set -e

echo "Starting ngrok on port $PORT ..."
if [ -n "$NGROK_DOMAIN" ]; then
  nohup "$NGROK_BIN" http --url="$NGROK_DOMAIN" "$PORT" > "$LOG_FILE" 2>&1 &
else
  nohup "$NGROK_BIN" http "$PORT" > "$LOG_FILE" 2>&1 &
fi
PID=$!
echo $PID > "$PID_FILE"
echo "ngrok started (PID $PID). Log: $LOG_FILE"

exit 0

