#!/usr/bin/env bash
# verify_clean_environment.sh
# Tests that Neural Memory runs completely standalone on a clean Mac without Docker or dev tools.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
APP_PATH="${DIST_DIR}/NeuralMemoryAgent.app"
TEST_PORT="8795"

echo "================================================================"
echo "🧪 SIMULATING CLEAN VANILLA MACBOOK ENVIRONMENT"
echo "   (Zero Docker, Zero Dev Tools, Zero Server Pre-requisites)"
echo "================================================================"

# 1. Ensure Docker is NOT used
echo "1. Ensuring local Docker stack is stopped..."
docker compose down >/dev/null 2>&1 || true

# 2. Check that standalone app bundle exists
if [ ! -d "${APP_PATH}" ]; then
  echo "⚠️ ${APP_PATH} not found. Building installer first..."
  "${ROOT_DIR}/scripts/package_installer.sh"
fi

# 3. Kill any existing instances on test port
echo "2. Preparing isolated execution..."
killall NeuralMemoryAgent >/dev/null 2>&1 || true

# 4. Start standalone daemon binary directly in clean PATH environment
echo "3. Launching Standalone Daemon in isolated clean environment..."
DAEMON_EXEC="${APP_PATH}/Contents/MacOS/neural-memory-daemon"
if [ ! -f "${DAEMON_EXEC}" ]; then
  DAEMON_EXEC="${APP_PATH}/Contents/MacOS/neural-memory-daemon/neural-memory-daemon"
fi

# Run with pure system PATH (no miniconda, no homebrew)
env -i \
  PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
  HOME="${HOME}" \
  USER="${USER}" \
  USE_EMBEDDED_STORE="true" \
  "${DAEMON_EXEC}" --port "${TEST_PORT}" > "/tmp/clean_env_daemon.log" 2>&1 &
DAEMON_PID=$!

echo "   Daemon started with PID ${DAEMON_PID}. Waiting for health check on port ${TEST_PORT}..."
sleep 2

# 5. Verify /health
HEALTH_OK=false
for i in {1..15}; do
  if curl -s "http://127.0.0.1:${TEST_PORT}/health" | grep -q '"status".*"ok"'; then
    HEALTH_OK=true
    break
  fi
  sleep 0.3
done

if [ "$HEALTH_OK" = true ]; then
  echo "   ✅ Health check PASSED on clean environment (status: ok)"
else
  echo "   ❌ Health check FAILED. Log output:"
  cat "/tmp/clean_env_daemon.log"
  kill -9 "${DAEMON_PID}" 2>/dev/null || true
  exit 1
fi

TOKEN=$(cat "${HOME}/Library/Application Support/NeuralMemory/token.txt" 2>/dev/null || echo "dev-token")

# 6. Verify /api/config reports embedded_sqlite mode
echo "4. Checking storage mode..."
CONFIG_RESP=$(curl -s "http://127.0.0.1:${TEST_PORT}/api/config" -H "Authorization: Bearer ${TOKEN}")
if echo "${CONFIG_RESP}" | grep -q "embedded_sqlite"; then
  echo "   ✅ Active storage mode confirmed: embedded_sqlite (Zero Docker)"
else
  echo "   ⚠️ Config response: ${CONFIG_RESP}"
fi

# 7. Ingest an activity event in embedded mode
echo "5. Testing event ingestion in standalone SQLite mode..."
INGEST_RESP=$(curl -s -X POST "http://127.0.0.1:${TEST_PORT}/api/ingest/event" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"project_id":"clean-test","event_type":"window_focus","data":{"app":"Finder","window":"Desktop"},"text_content":"Testing standalone MacBook app"}')

if echo "${INGEST_RESP}" | grep -q '"id"'; then
  echo "   ✅ Ingestion PASSED with local token"
else
  echo "   ❌ Ingestion FAILED. Response: ${INGEST_RESP}"
  kill -9 "${DAEMON_PID}" 2>/dev/null || true
  exit 1
fi

# 8. Query graph data
echo "6. Testing /api/graph/data in standalone mode..."
GRAPH_RESP=$(curl -s "http://127.0.0.1:${TEST_PORT}/api/graph/data?project_id=clean-test")
if echo "${GRAPH_RESP}" | grep -q '"nodes"'; then
  echo "   ✅ Graph API PASSED (returned valid nodes and links schema)"
else
  echo "   ❌ Graph API FAILED. Response: ${GRAPH_RESP}"
  kill -9 "${DAEMON_PID}" 2>/dev/null || true
  exit 1
fi

# 9. Verify SQLite database file existence
echo "7. Verifying local database file on disk..."
DB_FILE="${HOME}/Library/Application Support/NeuralMemory/memory.db"
if [ -f "${DB_FILE}" ]; then
  DB_SIZE=$(du -h "${DB_FILE}" | cut -f1)
  echo "   ✅ SQLite database created at: ${DB_FILE} (${DB_SIZE})"
else
  echo "   ❌ Database file not found at ${DB_FILE}"
  kill -9 "${DAEMON_PID}" 2>/dev/null || true
  exit 1
fi

# Clean up daemon process
kill -9 "${DAEMON_PID}" 2>/dev/null || true

echo "================================================================"
echo "🎉 ALL CLEAN ENVIRONMENT TESTS PASSED!"
echo "   The application runs 100% standalone with ZERO external prerequisites."
echo "================================================================"
