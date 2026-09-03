# Neural Memory Server (`kg_mcp`)

The Python server package powers the core storage, cognition, and agent integration layers of Neural Memory.

---

## 1. Core Architecture

The server provides four principal subsystem boundaries:

1. **Authenticated REST API (FastAPI)**:
   - Ingests raw events and multimodal interaction bundles.
   - Provides graph data endpoints with temporal filtering (`since`/`until`).
   - Runs memory consolidation and reflection cycles (Dream Mode).
2. **Dual-Track Storage Engine**:
   - **Standalone Mode (Embedded SQLite)**: Self-contained zero-dependency property graph in WAL mode stored at `~/Library/Application Support/NeuralMemory/memory.db`.
   - **Open Local Mode (Neo4j 5.26)**: Asynchronous Cypher driver connecting to `bolt://127.0.0.1:8787` for large-scale enterprise graph exploration.
3. **Cognitive & Privacy Services**:
   - **`PrivacyShield`**: Local regex + Luhn checksum redaction of credit cards, IBANs, API keys, and sensitive windows.
   - **`VisionAnalyzer`**: Multimodal extraction resolving ambiguous micro-feedback (*"Ok"*, *"Procedi"*) into semantic `Decision`, `Commitment`, and `Meeting` nodes.
   - **`MemoryConsolidator`**: Prunes ephemeral low-level events, deduplicates synonymous topics, and derives higher-order reflections.
4. **Model Context Protocol (MCP) Interface**:
   - Exposes standard stdio tools for Claude Desktop, Cursor, Antigravity, and OpenCode.

---

## 2. API Endpoints Reference

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Public | Returns service identity and version (`0.2.0`). |
| `POST` | `/api/ingest/event` | Bearer | Ingests a single raw event (window focus, keystroke, screenshot). |
| `POST` | `/api/ingest/bundle` | Bearer | Ingests a multimodal action bundle (screen context + typed text). |
| `GET` | `/api/graph/data` | Public | Returns graph `{nodes: [...], links: [...]}` with optional `since` and `until` filters. |
| `POST` | `/api/search/deep` | Bearer | Semantic hybrid search across topics, decisions, and artifacts. |
| `POST` | `/api/memory/consolidate` | Bearer | Runs ephemeral event pruning and topic deduplication. |
| `POST` | `/api/memory/dream` | Bearer | Manually triggers a Dream Mode reflection synthesis cycle. |
| `GET` | `/api/memory/reflections`| Bearer | Recalls synthesized reflections by category and topic. |
| `GET` | `/api/memory/briefing` | Bearer | Generates an executive daily briefing. |
| `GET` | `/api/config` | Bearer | Returns runtime configuration and active `storage_mode`. |
| `GET` | `/graph` | Public | Serves the embedded HTML5 / D3.js interactive graph visualizer. |

---

## 3. Local Development Setup

```bash
cd server
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running Backend Tests
```bash
pytest -q
```
Runs 74 automated unit tests, chaos fuzzers, and embedded SQLite lifecycle tests in under 2 seconds.

### Starting the Server Manually
```bash
# In standalone SQLite mode:
USE_EMBEDDED_STORE=true python -m kg_mcp.daemon_entry --port 8765

# In Open Local Neo4j mode:
kg-mcp --transport http --port 8765

# In MCP stdio mode for AI agents:
kg-mcp --transport stdio
```

---

## 4. Standalone Mach-O Binary Compilation

The standalone daemon is compiled with PyInstaller into a self-contained Mach-O arm64 binary:

```bash
server/.venv/bin/pyinstaller --clean -y \
  --name neural-memory-daemon \
  --add-data "server/src/kg_mcp/web/graph.html:kg_mcp/web" \
  --paths server/src \
  server/src/kg_mcp/daemon_entry.py
```
This binary is embedded inside `dist/NeuralMemoryAgent.app/Contents/MacOS/neural-memory-daemon`.

---

## 5. Configuration Reference (`.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `KG_MCP_TOKEN` | *Auto-generated* | Bearer authentication token for API routes. |
| `NEO4J_URI` | `bolt://127.0.0.1:8787` | Bolt connection URI for Open Local Neo4j. |
| `NEO4J_PASSWORD` | *Empty* | Password for Neo4j. If unset, activates embedded SQLite mode. |
| `USE_EMBEDDED_STORE` | `false` | Explicitly forces the embedded SQLite store. |
| `LLM_ENABLED` | `false` | Enables multimodal LLM enrichment. |
| `LLM_MODE` | `litellm` | Gateway mode (`litellm` or `gemini`). |
| `LITELLM_BASE_URL` | *None* | Base URL for OpenAI-compatible LiteLLM proxy. |
| `LITELLM_API_KEY` | *None* | API key for LiteLLM. |
| `LITELLM_MODEL` | `gpt-4o-mini` | Target vision model for enrichment. |
