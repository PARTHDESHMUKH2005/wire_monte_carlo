#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/parthdeshmukh/Desktop/final_fol"
cd "$PROJECT_DIR"

TUNNEL_LOG_DIR="/tmp/liverisk-tunnels"
BACKEND_LOG="$TUNNEL_LOG_DIR/backend.log"
FRONTEND_LOG="$TUNNEL_LOG_DIR/frontend.log"
URLS_FILE="$TUNNEL_LOG_DIR/urls.txt"

mkdir -p "$TUNNEL_LOG_DIR"

cleanup() {
  pkill -f "cloudflared tunnel.*localhost:8000" 2>/dev/null || true
  pkill -f "cloudflared tunnel.*localhost:3000" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
cleanup

cloudflared tunnel --url http://localhost:8000 > "$BACKEND_LOG" 2>&1 &
cloudflared tunnel --url http://localhost:3000 > "$FRONTEND_LOG" 2>&1 &

BACKEND_URL=""
FRONTEND_URL=""

for i in $(seq 1 30); do
  BACKEND_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$BACKEND_LOG" | head -1)
  FRONTEND_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$FRONTEND_LOG" | head -1)
  [ -n "$BACKEND_URL" ] && [ -n "$FRONTEND_URL" ] && break
  sleep 1
done

if [ -z "$BACKEND_URL" ] || [ -z "$FRONTEND_URL" ]; then
  echo "FAILED to get tunnel URLs" >&2
  exit 1
fi

echo "$BACKEND_URL" > "$URLS_FILE"
echo "$FRONTEND_URL" >> "$URLS_FILE"

CURRENT_BACKEND=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' docker-compose.yml | head -1 || true)
CURRENT_FRONTEND=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' docker-compose.yml | tail -1 || true)

if [ "$BACKEND_URL" != "$CURRENT_BACKEND" ] || [ "$FRONTEND_URL" != "$CURRENT_FRONTEND" ]; then
  sed -i '' "s|CORS_ORIGINS=https://[a-z0-9-]*\.trycloudflare\.com|CORS_ORIGINS=$FRONTEND_URL|" docker-compose.yml
  sed -i '' "s|NEXT_PUBLIC_API_URL=https://[a-z0-9-]*\.trycloudflare\.com|NEXT_PUBLIC_API_URL=$BACKEND_URL|" docker-compose.yml
  docker compose build frontend 2>&1 | tail -1
  docker compose up -d --force-recreate frontend 2>&1 | tail -1
fi

osascript -e "display notification \"Frontend: $FRONTEND_URL\" with title \"LiveRisk Tunnels Active\""
echo "Frontend: $FRONTEND_URL"
echo "Backend:  $BACKEND_URL"

wait
