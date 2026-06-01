#!/usr/bin/env bash
set -euo pipefail

# LiveRisk Deployment Script
# Usage: ./deploy.sh [--build] [--port-backend PORT] [--port-frontend PORT]
#
# Prerequisites:
#   1. Docker + Docker Compose installed
#   2. .env file configured (see .env.example)
#   3. Ports 8000 and 3000 available (or set via args)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Parse args
BUILD=false
BACKEND_PORT=8000
FRONTEND_PORT=3000

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build) BUILD=true ;;
    --port-backend) BACKEND_PORT="$2"; shift ;;
    --port-frontend) FRONTEND_PORT="$2"; shift ;;
    --help)
      echo "Usage: ./deploy.sh [--build] [--port-backend PORT] [--port-frontend PORT]"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

# Check prerequisites
if ! command -v docker &>/dev/null; then
  echo "ERROR: Docker not found. Install it first: https://docs.docker.com/engine/install/"
  exit 1
fi

if ! docker compose version &>/dev/null; then
  echo "ERROR: Docker Compose not found."
  exit 1
fi

# Check .env
if [ ! -f .env ]; then
  echo "ERROR: .env file not found. Copy .env.example to .env and configure it."
  exit 1
fi

# Check required env vars
if grep -q "your_wire_api_key_here" .env 2>/dev/null; then
  echo "WARNING: WIRE_API_KEY is still set to the placeholder value."
fi
if grep -q "your_groq_api_key_here" .env 2>/dev/null; then
  echo "WARNING: GROQ_API_KEY is still set to the placeholder value."
fi
if grep -q "change_this_to_a_random" .env 2>/dev/null; then
  echo "WARNING: JWT_SECRET is still set to the placeholder value. Generate a secure one."
fi

export BACKEND_PORT
export FRONTEND_PORT

# Build if requested
if [ "$BUILD" = true ]; then
  echo "==> Building images..."
  docker compose build
fi

echo "==> Starting services..."
docker compose up -d

echo "==> Waiting for backend health check..."
for i in $(seq 1 30); do
  if python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:$BACKEND_PORT/health')" 2>/dev/null; then
    echo "     Backend healthy on port $BACKEND_PORT"
    break
  fi
  sleep 2
done

echo ""
echo "==> LiveRisk deployed successfully!"
echo "     Frontend: http://localhost:$FRONTEND_PORT"
echo "     Backend:  http://localhost:$BACKEND_PORT"
echo ""
echo "     To stop:  docker compose down"
echo "     To view logs: docker compose logs -f"
