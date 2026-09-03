# Neural Memory server

The Python package provides three boundaries:

- an authenticated local FastAPI ingestion API
- a Neo4j repository and graph schema
- the original project-memory MCP tools over stdio

The supported zero-configuration path is the Docker Compose stack in the repository root. For development:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
kg-mcp --help
```

Configuration comes from environment variables or the root `.env`. LLM enrichment is optional and disabled by default. The HTTP server fails closed if `NEO4J_PASSWORD` or `KG_MCP_TOKEN` is missing.

`mcp` is intentionally constrained to the compatible 1.x API. Supporting the 2.x SDK requires a deliberate protocol migration rather than an untested dependency upgrade.
