#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Desktop or a compatible Docker engine." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required." >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl is required to generate local credentials." >&2
    exit 1
  fi
  umask 077
  neo4j_password="$(openssl rand -hex 24)"
  api_token="$(openssl rand -hex 32)"
  sed \
    -e "s/replace_with_random_database_password/$neo4j_password/" \
    -e "s/replace_with_random_api_token/$api_token/" \
    .env.example > .env
  echo "Created .env with local random credentials."
else
  echo "Keeping the existing .env."
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is installed but not running. Start it and run this script again." >&2
  exit 1
fi

docker compose config --quiet
docker compose up --detach --build

echo "Waiting for Neural Memory..."
for _ in $(seq 1 60); do
  if curl --fail --silent http://127.0.0.1:${NEURAL_MEMORY_PORT:-8765}/health >/dev/null 2>&1; then
    echo "Neural Memory is ready at http://127.0.0.1:${NEURAL_MEMORY_PORT:-8765}"
    echo "Copy KG_MCP_TOKEN from .env into a capture client before enabling it."
    exit 0
  fi
  sleep 2
done

echo "The service did not become healthy. Inspect it with: docker compose logs api neo4j" >&2
exit 1
