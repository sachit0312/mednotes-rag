#!/usr/bin/env bash
set -euo pipefail

# Sync Vercel env VITE_API_BASE_URL to current ngrok https URL and deploy.
# Prereqs: ngrok running (http 8000), Vercel CLI logged in and linked in ./web
# Usage: ./scripts/update_vercel_api_base.sh [production|preview]

ENVIRONMENT="${1:-production}"
NGROK_API_URL="${NGROK_API_URL:-http://127.0.0.1:4040/api/tunnels}"
NGROK_DOMAIN="${NGROK_DOMAIN:-}"

if [ -n "$NGROK_DOMAIN" ]; then
  if [[ "$NGROK_DOMAIN" == http* ]]; then
    NGROK_URL="$NGROK_DOMAIN"
  else
    NGROK_URL="https://${NGROK_DOMAIN}"
  fi
  echo "Using static ngrok domain: ${NGROK_URL}"
else
  echo "Fetching ngrok public https tunnel..."
  NGROK_URL=$(python3 - <<'PY'
import json, sys, urllib.request, os
u = os.environ.get('NGROK_API_URL', 'http://127.0.0.1:4040/api/tunnels')
with urllib.request.urlopen(u) as r:
    data = json.loads(r.read().decode('utf-8'))
ts = [t.get('public_url') for t in data.get('tunnels', []) if t.get('proto') == 'https']
print(ts[0] if ts else '')
PY
  )
  if [ -z "${NGROK_URL}" ]; then
    echo "No ngrok https tunnel found at ${NGROK_API_URL}. Is 'ngrok http 8000' running?" >&2
    exit 1
  fi
  echo "Using API base URL: ${NGROK_URL}"
fi
echo "Linking Vercel project in ./web (if not already)..."
cd web
vercel link >/dev/null 2>&1 || true

echo "Setting Vercel env VITE_API_BASE_URL for ${ENVIRONMENT} (interactive if needed)..."
# Avoid removing existing; adding a new value supersedes prior value in Vercel UI.
printf "%s" "${NGROK_URL}" | vercel env add VITE_API_BASE_URL "${ENVIRONMENT}"

echo "Deploying..."
vercel --prod

echo "Done. UI now calls: ${NGROK_URL}"
