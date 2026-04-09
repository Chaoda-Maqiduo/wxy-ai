#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_DIR"

IMAGE_NAME="${IMAGE_NAME:-wxy-ai:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-wxy-ai}"
ENV_FILE="${ENV_FILE:-.env}"
CONTAINER_PORT="${CONTAINER_PORT:-}"
HOST_PORT="${HOST_PORT:-}"
NETWORK_NAME="${NETWORK_NAME:-}"
BUILD_NO_CACHE="${BUILD_NO_CACHE:-false}"

log() {
  printf '[start.sh] %s\n' "$*"
}

fail() {
  printf '[start.sh][ERROR] %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<EOF
Usage:
  sh start.sh

Optional environment variables:
  IMAGE_NAME       Docker image tag (default: wxy-ai:latest)
  CONTAINER_NAME   Docker container name (default: wxy-ai)
  ENV_FILE         Env file path (default: .env)
  HOST_PORT        Host port exposed to outside (default: same as CONTAINER_PORT)
  CONTAINER_PORT   Container listening port (default: APP_PORT in .env, fallback 10461)
  NETWORK_NAME     Docker network name to attach (optional)
  BUILD_NO_CACHE   true/1 to disable Docker build cache (default: false)

Example:
  HOST_PORT=8080 CONTAINER_NAME=wxy-ai-prod sh start.sh
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

command -v docker >/dev/null 2>&1 || fail "Docker is not installed or not in PATH."
docker info >/dev/null 2>&1 || fail "Docker daemon is not running."

[ -f "$ENV_FILE" ] || fail "Env file not found: $ENV_FILE"
[ -f "Dockerfile" ] || fail "Dockerfile not found in $PROJECT_DIR"

if [ -z "$HOST_PORT" ]; then
  APP_PORT_FROM_ENV=$(awk -F= '/^[[:space:]]*APP_PORT=/{print $2}' "$ENV_FILE" | tail -n 1 | tr -d '\r' | tr -d ' ')
  if [ -z "$CONTAINER_PORT" ]; then
    CONTAINER_PORT="$APP_PORT_FROM_ENV"
  fi
  [ -n "$CONTAINER_PORT" ] || CONTAINER_PORT="10461"
  HOST_PORT="$CONTAINER_PORT"
else
  if [ -z "$CONTAINER_PORT" ]; then
    APP_PORT_FROM_ENV=$(awk -F= '/^[[:space:]]*APP_PORT=/{print $2}' "$ENV_FILE" | tail -n 1 | tr -d '\r' | tr -d ' ')
    CONTAINER_PORT="$APP_PORT_FROM_ENV"
    [ -n "$CONTAINER_PORT" ] || CONTAINER_PORT="10461"
  fi
fi

REDIS_URL=$(awk -F= '/^[[:space:]]*REDIS_URL=/{print $2}' "$ENV_FILE" | tail -n 1 | tr -d '\r' | tr -d ' ')
if [ -n "$REDIS_URL" ]; then
  case "$REDIS_URL" in
    redis://localhost:*|redis://127.0.0.1:*|rediss://localhost:*|rediss://127.0.0.1:*)
      log "WARNING: REDIS_URL points to localhost/127.0.0.1. Inside container this is itself, not host Redis."
      log "WARNING: Use a reachable Redis host (for example redis://host.docker.internal:6379/0 or redis://<redis-service>:6379/0)."
      ;;
  esac
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
  log "Removing existing container: $CONTAINER_NAME"
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

log "Building image: $IMAGE_NAME"
if [ "$BUILD_NO_CACHE" = "true" ] || [ "$BUILD_NO_CACHE" = "1" ]; then
  docker build --pull --no-cache -t "$IMAGE_NAME" .
else
  docker build --pull -t "$IMAGE_NAME" .
fi

log "Starting container: $CONTAINER_NAME"
if [ -n "$NETWORK_NAME" ]; then
  CONTAINER_ID=$(docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --env-file "$ENV_FILE" \
    --network "$NETWORK_NAME" \
    -v "${PROJECT_DIR}/app/output:/app/app/output" \
    -p "${HOST_PORT}:${CONTAINER_PORT}" \
    "$IMAGE_NAME")
else
  CONTAINER_ID=$(docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --env-file "$ENV_FILE" \
    -v "${PROJECT_DIR}/app/output:/app/app/output" \
    -p "${HOST_PORT}:${CONTAINER_PORT}" \
    "$IMAGE_NAME")
fi

sleep 2
RUNNING=$(docker inspect --format '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || true)
[ "$RUNNING" = "true" ] || fail "Container failed to start. Check logs: docker logs $CONTAINER_NAME"

HEALTH=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTAINER_NAME" 2>/dev/null || true)

log "Container id: $CONTAINER_ID"
log "Service URL: http://localhost:${HOST_PORT}"
log "Health endpoint: http://localhost:${HOST_PORT}/health"
log "Container health: $HEALTH"
log "View logs: docker logs -f $CONTAINER_NAME"
