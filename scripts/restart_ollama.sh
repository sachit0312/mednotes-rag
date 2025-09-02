#!/usr/bin/env bash
# Restart local Ollama daemon: kill existing and start a fresh server.
# Usage: bash scripts/restart_ollama.sh

set -euo pipefail

LOG_FILE=${LOG_FILE:-ollama.log}
PID_FILE=${PID_FILE:-ollama.pid}
BASE_URL=${OLLAMA_BASE_URL:-http://localhost:11434}

echo "Stopping any existing ollama serve..."
set +e
pkill -f "ollama" 2>/dev/null
set -e

echo "Starting ollama serve in background..."
nohup ollama serve > "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"

echo "Waiting for Ollama to respond at $BASE_URL ..."
for i in {1..30}; do
  if curl -fsS "$BASE_URL/api/version" >/dev/null 2>&1; then
    echo "Ollama is up (PID $PID)."
    exit 0
  fi
  sleep 1
done

echo "Warning: Ollama did not respond in time. See $LOG_FILE (PID $PID)."
exit 0

