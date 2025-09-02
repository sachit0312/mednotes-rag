#!/usr/bin/env bash
# Deploy the Vite web UI to Vercel with the correct API base URL.
#
# Usage examples:
#   ./scripts/deploy_vercel_ui.sh                     # production, auto-detect API URL
#   ./scripts/deploy_vercel_ui.sh preview             # preview env
#   API_BASE_URL=https://api.example.com ./scripts/deploy_vercel_ui.sh production
#   NGROK_DOMAIN=flea-whole-loosely.ngrok-free.app ./scripts/deploy_vercel_ui.sh production
#
# Resolution order for API base URL:
# 1) $API_BASE_URL if provided
# 2) https://$NGROK_DOMAIN if provided
# 3) First https tunnel from ngrok local API (http://127.0.0.1:4040/api/tunnels)

set -euo pipefail

# Load repo deploy defaults if present
if [ -f "$(dirname "$0")/../deploy.env" ]; then
  # shellcheck disable=SC1091
  . "$(dirname "$0")/../deploy.env"
fi

ENVIRONMENT="${1:-production}"
API_BASE_URL="${API_BASE_URL:-}"
NGROK_DOMAIN="${NGROK_DOMAIN:-}"
NGROK_API_URL="${NGROK_API_URL:-http://127.0.0.1:4040/api/tunnels}"

resolve_api_base() {
  if [ -n "$API_BASE_URL" ]; then
    echo "$API_BASE_URL"
    return 0
  fi
  if [ -n "$NGROK_DOMAIN" ]; then
    # ensure https scheme
    if [[ "$NGROK_DOMAIN" == http* ]]; then
      echo "$NGROK_DOMAIN"
    else
      echo "https://${NGROK_DOMAIN}"
    fi
    return 0
  fi
  # Try local ngrok API as a fallback
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<PY || true
import json, sys, urllib.request, os
u = os.environ.get('NGROK_API_URL', 'http://127.0.0.1:4040/api/tunnels')
try:
    with urllib.request.urlopen(u) as r:
        data = json.loads(r.read().decode('utf-8'))
    for t in data.get('tunnels', []):
        if t.get('proto') == 'https':
            print(t.get('public_url'))
            sys.exit(0)
except Exception:
    pass
sys.exit(1)
PY
  fi
}

API_URL=$(resolve_api_base || true)
if [ -z "$API_URL" ]; then
  echo "Error: Could not resolve API base URL. Set API_BASE_URL or NGROK_DOMAIN, or run ngrok locally." >&2
  exit 1
fi

echo "Using API base URL: $API_URL"

pushd web >/dev/null
  # Ensure project is linked
  vercel link --yes >/dev/null 2>&1 || true

  # Set env var in Vercel for the target environment (adds a new value if one exists)
  # Best-effort: remove existing value to avoid interactive overwrite prompt
  vercel env rm VITE_API_BASE_URL "$ENVIRONMENT" --yes >/dev/null 2>&1 || true
  printf "%s" "$API_URL" | vercel env add VITE_API_BASE_URL "$ENVIRONMENT"

  # Deploy
  if [ "$ENVIRONMENT" = "production" ]; then
    vercel deploy --prod --yes
  else
    vercel deploy --yes
  fi
popd >/dev/null

echo "Done. Deployed UI configured to call: $API_URL"
