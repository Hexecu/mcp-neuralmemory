#!/usr/bin/env bash
set -u

failed=0
check() {
  if eval "$2" >/dev/null 2>&1; then
    printf 'ok    %s\n' "$1"
  else
    printf 'fail  %s\n' "$1"
    failed=1
  fi
}

check "Docker CLI" "command -v docker"
check "Docker Compose v2" "docker compose version"
check "Docker engine" "docker info"
check "Local configuration" "test -f .env"
check "API health" "curl --fail --silent http://127.0.0.1:${NEURAL_MEMORY_PORT:-8765}/health"

exit "$failed"
