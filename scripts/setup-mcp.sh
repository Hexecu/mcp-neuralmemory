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

mcp_bin="$project_dir/server/.venv/bin/kg-mcp"
if [[ ! -x "$mcp_bin" ]]; then
  echo "⚙️ Building virtualenv in server/.venv..."
  python3 -m venv "$project_dir/server/.venv"
  "$project_dir/server/.venv/bin/pip" install -q -e "$project_dir/server"
fi

bolt_port="${NEO4J_BOLT_PORT:-8787}"
bolt_uri="${NEO4J_URI:-bolt://127.0.0.1:$bolt_port}"

claude_json=$(cat <<EOJSON
{
  "mcpServers": {
    "neural-memory": {
      "command": "$mcp_bin",
      "args": ["--transport", "stdio"],
      "env": {
        "NEO4J_URI": "$bolt_uri",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "$NEO4J_PASSWORD",
        "KG_MCP_TOKEN": "$KG_MCP_TOKEN"
      }
    }
  }
}
EOJSON
)

cursor_json=$(cat <<EOJSON
{
  "mcpServers": {
    "neural-memory": {
      "command": "$mcp_bin",
      "args": ["--transport", "stdio"],
      "env": {
        "NEO4J_URI": "$bolt_uri",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "$NEO4J_PASSWORD",
        "KG_MCP_TOKEN": "$KG_MCP_TOKEN"
      }
    }
  }
}
EOJSON
)

echo "================================================================"
echo "🧠 Neural Memory MCP Configuration for AI Assistants"
echo "================================================================"
echo ""
echo "📋 Claude Desktop Configuration:"
echo "Add this to: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo ""
echo "$claude_json"
echo ""
echo "📋 Cursor Configuration:"
echo "Add this to: ~/.cursor/mcp.json or .cursor/mcp.json"
echo ""
echo "$cursor_json"
echo "================================================================"

if [[ "${1:-}" == "--install" || "${1:-}" == "--claude" ]]; then
  claude_dir="$HOME/Library/Application Support/Claude"
  claude_config="$claude_dir/claude_desktop_config.json"
  if [[ -d "$claude_dir" ]]; then
    if [[ -f "$claude_config" ]]; then
      cp "$claude_config" "${claude_config}.bak.$(date +%s)"
      echo "Backed up existing Claude config."
    fi
    python3 - <<PY
import json, os

config_path = "$claude_config"
entry = json.loads('''$claude_json''')

current = {}
if os.path.exists(config_path):
    try:
        current = json.load(open(config_path))
    except Exception:
        current = {}

if "mcpServers" not in current:
    current["mcpServers"] = {}

current["mcpServers"]["neural-memory"] = entry["mcpServers"]["neural-memory"]

with open(config_path, "w") as f:
    json.dump(current, f, indent=2)

print("✅ Successfully updated Claude Desktop MCP configuration at:", config_path)
PY
  else
    echo "Note: Claude Desktop directory not found at $claude_dir"
  fi
fi
