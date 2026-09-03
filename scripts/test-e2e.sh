#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if [[ ! -f .env ]]; then
  echo "⚠️ .env not found. Running ./scripts/bootstrap.sh first..."
  ./scripts/bootstrap.sh
fi

set -a
source "$project_dir/.env"
set +a

PORT="${NEURAL_MEMORY_PORT:-8765}"
BASE_URL="http://127.0.0.1:${PORT}"
TOKEN="${KG_MCP_TOKEN}"
TEST_PROJECT="e2e-$(date +%s)"

echo "================================================================"
echo "🧪 Running Neural Memory End-to-End (E2E) Test Suite"
echo "   Target: $BASE_URL"
echo "================================================================"

pass_count=0
fail_count=0

assert_step() {
  local desc="$1"
  local cmd="$2"
  printf "Testing %-55s ... " "$desc"
  if output=$(eval "$cmd" 2>&1); then
    printf "✅ PASS\n"
    pass_count=$((pass_count + 1))
  else
    printf "❌ FAIL\n"
    echo "   Error: $output"
    fail_count=$((fail_count + 1))
  fi
}

# 1. Health check
assert_step "Health check identity (/health)" \
  "python3 -c '
import urllib.request, json
res = urllib.request.urlopen(\"$BASE_URL/health\", timeout=5)
data = json.loads(res.read())
assert data[\"status\"] == \"ok\", f\"bad status: {data}\"
assert data[\"service\"] == \"neural-memory\", f\"bad service: {data}\"
assert \"version\" in data, f\"missing version: {data}\"
'"

# 2. Unauthorized rejection (missing token)
assert_step "Reject event without authorization (401)" \
  "python3 -c '
import urllib.request, urllib.error
req = urllib.request.Request(\"$BASE_URL/api/ingest/event\", data=b\"{}\", headers={\"Content-Type\": \"application/json\"}, method=\"POST\")
try:
    urllib.request.urlopen(req, timeout=5)
    exit(1)
except urllib.error.HTTPError as e:
    assert e.code == 401, f\"Expected 401, got {e.code}\"
'"

# 3. Forbidden rejection (invalid token)
assert_step "Reject event with invalid authorization (403)" \
  "python3 -c '
import urllib.request, urllib.error
req = urllib.request.Request(\"$BASE_URL/api/ingest/event\", data=b\"{}\", headers={\"Content-Type\": \"application/json\", \"Authorization\": \"Bearer invalid-token\"}, method=\"POST\")
try:
    urllib.request.urlopen(req, timeout=5)
    exit(1)
except urllib.error.HTTPError as e:
    assert e.code == 403, f\"Expected 403, got {e.code}\"
'"

# 4. Ingest raw text event
assert_step "Ingest raw activity event with Bearer token" \
  "python3 -c '
import urllib.request, json
payload = {
    \"project_id\": \"$TEST_PROJECT\",
    \"event_type\": \"window_focus\",
    \"data\": {\"app\": \"VSCode\", \"window\": \"NeuralMemory\"},
    \"text_content\": \"Working on Neural Memory E2E test\"
}
req = urllib.request.Request(
    \"$BASE_URL/api/ingest/event\",
    data=json.dumps(payload).encode(),
    headers={\"Content-Type\": \"application/json\", \"Authorization\": \"Bearer $TOKEN\"},
    method=\"POST\"
)
res = urllib.request.urlopen(req, timeout=5)
assert res.status == 200
data = json.loads(res.read())
assert \"id\" in data and data[\"id\"], f\"Missing id in response: {data}\"
open(\"/tmp/e2e_event_id.txt\", \"w\").write(data[\"id\"])
'"

# 5. Ingest screenshot and test deduplication
assert_step "Ingest screenshot with visual hashing" \
  "python3 -c '
import urllib.request, json
# 1x1 transparent PNG base64
png_b64 = \"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==\"
payload = {
    \"project_id\": \"$TEST_PROJECT\",
    \"event_type\": \"screenshot\",
    \"data\": {\"app\": \"Browser\", \"has_screenshot\": True},
    \"screenshot_base64\": png_b64
}
req = urllib.request.Request(
    \"$BASE_URL/api/ingest/event\",
    data=json.dumps(payload).encode(),
    headers={\"Content-Type\": \"application/json\", \"Authorization\": \"Bearer $TOKEN\"},
    method=\"POST\"
)
res = urllib.request.urlopen(req, timeout=5)
data = json.loads(res.read())
assert \"id\" in data and data[\"id\"], f\"Missing id: {data}\"
assert data.get(\"screenshot_hash\"), f\"Missing hash: {data}\"
assert not data.get(\"is_duplicate\"), f\"Should not be duplicate: {data}\"
open(\"/tmp/e2e_first_shot_id.txt\", \"w\").write(data[\"id\"])
'"

assert_step "Screenshot deduplication detects identical frame" \
  "python3 -c '
import urllib.request, json
png_b64 = \"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==\"
payload = {
    \"project_id\": \"$TEST_PROJECT\",
    \"event_type\": \"screenshot\",
    \"data\": {\"app\": \"Browser\", \"has_screenshot\": True},
    \"screenshot_base64\": png_b64
}
req = urllib.request.Request(
    \"$BASE_URL/api/ingest/event\",
    data=json.dumps(payload).encode(),
    headers={\"Content-Type\": \"application/json\", \"Authorization\": \"Bearer $TOKEN\"},
    method=\"POST\"
)
res = urllib.request.urlopen(req, timeout=5)
data = json.loads(res.read())
first_id = open(\"/tmp/e2e_first_shot_id.txt\").read().strip()
assert data.get(\"is_duplicate\") == True, f\"Expected is_duplicate=True: {data}\"
assert data.get(\"duplicate_of\") == first_id, f\"Expected duplicate_of={first_id}: {data}\"
'"

# 6. Ingest activity slice
assert_step "Ingest activity slice" \
  "python3 -c '
import urllib.request, json
event_id = open(\"/tmp/e2e_event_id.txt\").read().strip()
payload = {
    \"project_id\": \"$TEST_PROJECT\",
    \"summary\": \"Refactored test suite and validated E2E flow\",
    \"event_ids\": [event_id],
    \"start_time\": \"2026-09-03T00:00:00Z\",
    \"end_time\": \"2026-09-03T01:00:00Z\"
}
req = urllib.request.Request(
    \"$BASE_URL/api/ingest/slice\",
    data=json.dumps(payload).encode(),
    headers={\"Content-Type\": \"application/json\", \"Authorization\": \"Bearer $TOKEN\"},
    method=\"POST\"
)
res = urllib.request.urlopen(req, timeout=5)
data = json.loads(res.read())
assert \"id\" in data and data[\"id\"], f\"Missing slice id: {data}\"
'"

# 7. Deep search query
assert_step "Query deep search endpoint" \
  "python3 -c '
import urllib.request, json
payload = {
    \"project_id\": \"$TEST_PROJECT\",
    \"query\": \"Neural Memory\",
    \"limit\": 5
}
req = urllib.request.Request(
    \"$BASE_URL/api/search/deep\",
    data=json.dumps(payload).encode(),
    headers={\"Content-Type\": \"application/json\", \"Authorization\": \"Bearer $TOKEN\"},
    method=\"POST\"
)
res = urllib.request.urlopen(req, timeout=5)
data = json.loads(res.read())
assert isinstance(data, (dict, list)), f\"Unexpected deep search response: {type(data)}\"
'"

# 8. MCP stdio protocol check
assert_step "MCP stdio server protocol handshake" \
  "python3 -c '
import subprocess, json

proc = subprocess.Popen(
    [\"$project_dir/server/.venv/bin/kg-mcp\", \"--transport\", \"stdio\"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

init_req = {
    \"jsonrpc\": \"2.0\",
    \"id\": 1,
    \"method\": \"initialize\",
    \"params\": {
        \"protocolVersion\": \"2024-11-05\",
        \"capabilities\": {},
        \"clientInfo\": {\"name\": \"e2e-test\", \"version\": \"1.0\"}
    }
}

proc.stdin.write(json.dumps(init_req) + \"\n\")
proc.stdin.flush()

response_line = proc.stdout.readline()
proc.kill()

assert response_line, \"No response from MCP stdio server\"
resp = json.loads(response_line)
assert resp.get(\"id\") == 1, f\"Bad response ID: {resp}\"
assert \"result\" in resp, f\"Missing result: {resp}\"
assert resp[\"result\"][\"serverInfo\"][\"name\"] == \"Neural Memory\"
'"

echo "================================================================"
if [ "$fail_count" -eq 0 ]; then
  echo "🎉 All $pass_count E2E tests PASSED successfully!"
  exit 0
else
  echo "⚠️ $fail_count test(s) failed out of $((pass_count + fail_count))."
  exit 1
fi
