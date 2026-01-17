# MCP-KG-Memory Server

Python MCP server implementation with Neo4j backend.

## Development Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies (including dev)
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run server
python -m kg_mcp.main
```

## Project Structure

```
src/kg_mcp/
├── main.py           # Entry point
├── config.py         # Settings management
├── llm/              # LLM integration
│   ├── client.py     # LiteLLM wrapper
│   ├── schemas.py    # Pydantic models
│   └── prompts/      # Prompt templates
├── kg/               # Knowledge graph
│   ├── neo4j.py      # Driver/client
│   ├── schema.cypher # DB schema
│   ├── repo.py       # Query repository
│   ├── ingest.py     # Ingestion pipeline
│   └── retrieval.py  # Context builder
├── mcp/              # MCP components
│   ├── tools.py      # Tool definitions
│   ├── resources.py  # Resource handlers
│   └── prompts.py    # Prompt templates
├── codegraph/        # Code indexing (V1)
│   ├── model.py      # Data models
│   └── indexer.py    # File indexer
└── security/         # Auth/Origin
    ├── auth.py       # Token validation
    └── origin.py     # Origin checking
```
