# MCP-KG-Memory

<div align="center">

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)
![MCP](https://img.shields.io/badge/MCP-1.0+-purple.svg)

**Memory/Knowledge Graph MCP Server for AI Coding Assistants**

*Persistent context, goals, preferences, and knowledge for IDE agents*

[Quick Start](#-quick-start) • [Features](#-features) • [IDE Setup](#-ide-configuration) • [API Reference](#-mcp-tools) • [Contributing](#-contributing)

</div>

---

## 🎯 What is MCP-KG-Memory?

MCP-KG-Memory is a **Model Context Protocol (MCP) server** that provides persistent memory and knowledge management for AI coding assistants. It solves the problem of AI agents "forgetting" context between sessions by:

- **Extracting structured information** from every user request (goals, constraints, preferences)
- **Building a knowledge graph** in Neo4j that persists across sessions
- **Providing context packs** to AI agents so they never lose track of what matters
- **Tracking code artifacts** and their relationships to goals for impact analysis

### Why Use This?

| Without KG-Memory | With KG-Memory |
|-------------------|----------------|
| AI forgets previous context | Persistent memory across sessions |
| Repeated explanations needed | Learns your preferences once |
| No goal tracking | Structured goal management |
| Manual context switching | Automatic context packs |
| Unknown code impact | Impact analysis on changes |

---

## ✨ Features

### 🧠 Intelligent Ingestion
Analyzes every user request with Gemini LLM to extract:
- **Goals** with priority, status, and acceptance criteria
- **Constraints** (time, technical, budget)
- **Preferences** (coding style, architecture choices)
- **Pain Points** and blockers
- **Strategies** and approaches

### 📦 Context Packs
At each request, navigate the knowledge graph and return:
- Active goals with acceptance criteria
- User preferences and coding guidelines
- Open pain points and blockers
- Related code artifacts

### 🔗 Code Graph
Map files → symbols → references for:
- Goal-to-code traceability
- Impact analysis on changes
- Test coverage tracking

### 🔍 Hybrid Retrieval
- Graph traversal with k-hop neighbors
- Full-text search across all entities
- Semantic search (optional, with embeddings)

---

## 📋 Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.11+ | Required |
| **Docker** | Latest | For local Neo4j |
| **Neo4j** | 5.x | Provided via Docker or remote |
| **LLM API** | - | LiteLLM Gateway or Gemini API key |

---

## 🚀 Quick Start

### Option 1: Interactive Setup Wizard (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/mcp-kg-memory.git
cd mcp-kg-memory/server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install with setup wizard
pip install -e .
kg-mcp-setup
```

The wizard will guide you through:
1. Neo4j configuration (local Docker or remote)
2. LLM API setup (LiteLLM Gateway or Gemini direct)
3. Security token generation
4. Antigravity IDE integration

### Option 2: Manual Setup

```bash
# 1. Clone and setup
git clone https://github.com/your-org/mcp-kg-memory.git
cd mcp-kg-memory

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Create virtual environment
cd server
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 4. Start Neo4j
cd ..
docker compose up -d neo4j

# 5. Wait for Neo4j, then apply schema
sleep 30
python -m kg_mcp.kg.apply_schema

# 6. Start the server
kg-mcp --transport http
# Server available at http://127.0.0.1:8000/mcp
```

---

## 🖥️ CLI Reference

MCP-KG-Memory provides two CLI commands:

### `kg-mcp` - Run the MCP Server

```bash
# STDIO mode (for IDE command-based integration)
kg-mcp --transport stdio

# HTTP mode (for serverUrl-based integration)
kg-mcp --transport http --host 127.0.0.1 --port 8000

# All options
kg-mcp --help
```

| Option | Default | Description |
|--------|---------|-------------|
| `--transport, -t` | `http` | Transport mode: `stdio` or `http` |
| `--host` | `127.0.0.1` | Host to bind (HTTP mode) |
| `--port, -p` | `8000` | Port to listen (HTTP mode) |
| `--path` | `/mcp` | MCP endpoint path |

### `kg-mcp-setup` - Interactive Setup Wizard

```bash
kg-mcp-setup
```

Guides you through complete configuration with beautiful CLI output.

---

## 🔧 IDE Configuration

### Google Antigravity IDE ⭐

**Setup Steps:**
1. Open **Agent sidebar** → **...** (More Actions)
2. Select **MCP Servers**
3. Go to **Manage MCP Servers** → **View raw config**
4. Add the configuration below
5. Save and click **Refresh**

**Option A: Local Server (command/args)** ✅ *Recommended for development*

```json
{
  "mcpServers": {
    "kg-memory": {
      "command": "/path/to/mcp-kg-memory/server/.venv/bin/python",
      "args": ["-m", "kg_mcp", "--transport", "stdio"],
      "env": {
        "NEO4J_URI": "bolt://127.0.0.1:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your_password",
        "LITELLM_BASE_URL": "https://your-gateway.io/",
        "LITELLM_API_KEY": "your_key",
        "LLM_MODEL": "gemini-2.5-flash",
        "KG_MCP_TOKEN": "your_token"
      }
    }
  }
}
```

**Option B: Remote Server (serverUrl)** ✅ *For production/cloud*

```json
{
  "mcpServers": {
    "kg-memory": {
      "serverUrl": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer your_token"
      }
    }
  }
}
```

### VS Code

Create/edit `.vscode/mcp.json`:

```json
{
  "servers": {
    "kg-memory": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "authorization": "Bearer ${env:KG_MCP_TOKEN}"
      }
    }
  }
}
```

### Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "kg-memory": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "authorization": "Bearer ${env:KG_MCP_TOKEN}"
      }
    }
  }
}
```

### Cline / Roo Code

Add to `.cline/mcp_config.json`:

```json
{
  "mcpServers": {
    "kg-memory": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer ${KG_MCP_TOKEN}"
      }
    }
  }
}
```

---

## 📚 MCP Tools

### `kg_ingest_message`

Analyze and save a user request to the knowledge graph.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | ✅ | Project identifier |
| `user_text` | string | ✅ | User's message/request |
| `files` | string[] | ❌ | File paths involved |
| `diff` | string | ❌ | Code diff |
| `symbols` | string[] | ❌ | Code symbols |
| `tags` | string[] | ❌ | Tags for categorization |

**Returns:**
```json
{
  "interaction_id": "uuid",
  "extracted": {
    "goals": [...],
    "constraints": [...],
    "preferences": [...]
  },
  "created_entities": {"goals": [...], "constraints": [...]},
  "confidence": 0.85
}
```

---

### `kg_context_pack`

Build a comprehensive context pack from the knowledge graph.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | ✅ | Project identifier |
| `focus_goal_id` | string | ❌ | Specific goal to focus on |
| `query` | string | ❌ | Search query for additional context |
| `k_hops` | integer | ❌ | Graph traversal depth (1-5, default: 2) |

**Returns:**
```json
{
  "markdown": "# Context Pack\n\n## Active Goals\n...",
  "entities": {
    "active_goals": [...],
    "preferences": [...],
    "pain_points": [...]
  }
}
```

---

### `kg_search`

Search the knowledge graph with fulltext + traversal.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | ✅ | Project identifier |
| `query` | string | ✅ | Search query |
| `filters` | string[] | ❌ | Type filters (Goal, PainPoint, Strategy) |
| `limit` | integer | ❌ | Max results (default: 20) |

---

### `kg_link_code_artifact`

Link a code artifact to the knowledge graph.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | ✅ | Project identifier |
| `path` | string | ✅ | File path |
| `kind` | string | ❌ | Type: file, function, class, snippet |
| `language` | string | ❌ | Programming language |
| `symbol_fqn` | string | ❌ | Fully qualified symbol name |
| `related_goal_ids` | string[] | ❌ | Goals this artifact implements |

---

### `kg_impact_analysis`

Analyze the impact of code changes.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project_id` | string | ✅ | Project identifier |
| `changed_paths` | string[] | ❌ | Changed file paths |
| `changed_symbols` | string[] | ❌ | Changed symbol FQNs |

**Returns:**
```json
{
  "goals_to_retest": [...],
  "tests_to_run": [...],
  "strategies_to_review": [...],
  "artifacts_related": [...]
}
```

---

## 📖 MCP Resources

| URI Pattern | Description |
|-------------|-------------|
| `kg://projects/{id}/active-goals` | Active goals in markdown |
| `kg://projects/{id}/preferences` | User preferences |
| `kg://projects/{id}/goal/{goal_id}/subgraph` | Subgraph around a goal |
| `kg://projects/{id}/pain-points` | Open pain points |

---

## 💬 MCP Prompts

### `StartCodingWithKG`

Standard workflow prompt that instructs IDE agents to:
1. Call `kg_ingest_message` with the user request
2. Call `kg_context_pack` and use the markdown as context
3. When creating/modifying files, call `kg_link_code_artifact`

### `ReviewGoals`

Prompt for reviewing and managing project goals.

### `DebugWithContext`

Prompt for debugging using knowledge graph context.

### `DocumentPreferences`

Prompt for documenting user coding preferences.

---

## 🔒 Security

### Built-in Protections

| Feature | Description |
|---------|-------------|
| **Localhost Binding** | Server binds to `127.0.0.1` by default |
| **Bearer Token Auth** | Required authentication via `KG_MCP_TOKEN` |
| **Origin Validation** | Allowlist for cross-origin requests |
| **No Shell Execution** | No arbitrary command execution |
| **Audit Logging** | All operations logged |

### Environment Variables

```bash
# Required
KG_MCP_TOKEN=your-secret-token       # Auth token (32+ chars recommended)

# Optional security settings
KG_ALLOWED_ORIGINS=localhost,127.0.0.1   # Allowed origins
MCP_HOST=127.0.0.1                       # Bind address (keep localhost!)
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        IDE Agent                             │
│  (VS Code / Cursor / Antigravity with MCP Client)           │
└─────────────────────────┬───────────────────────────────────┘
                          │ MCP (Streamable HTTP / STDIO)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP-KG-Memory Server                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Tools     │  │  Resources  │  │      Prompts        │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         └────────────────┼─────────────────────┘             │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   LLM Pipeline                          ││
│  │  ┌───────────┐   ┌───────────┐   ┌─────────────────┐   ││
│  │  │ Extractor │ → │  Linker   │ → │ Neo4j Commit    │   ││
│  │  │ (Gemini)  │   │ (Gemini)  │   │                 │   ││
│  │  └───────────┘   └───────────┘   └─────────────────┘   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────┬───────────────────────────────────┘
                          │ Bolt Protocol
                          ▼
               ┌───────────────────────┐
               │        Neo4j          │
               │   (Knowledge Graph)   │
               └───────────────────────┘
```

### Knowledge Graph Schema

```
(User)──PREFERS──>(Preference)
(Project)──HAS_GOAL──>(Goal)──DECOMPOSES_INTO──>(Goal)
                   │
                   ├──HAS_CONSTRAINT──>(Constraint)
                   ├──HAS_STRATEGY──>(Strategy)
                   ├──BLOCKED_BY──>(PainPoint)
                   └──IMPLEMENTED_BY──>(CodeArtifact)──CONTAINS──>(Symbol)
                                                    │
                                                    └──COVERED_BY──>(TestCase)
```

---

## 🧪 Testing

```bash
cd server

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=kg_mcp --cov-report=html

# Run specific test file
pytest tests/test_ingest.py -v
```

---

## 🔧 Development

### Project Structure

```
mcp-kg-memory/
├── .env.example           # Environment template
├── docker-compose.yml     # Neo4j container
├── README.md              # This file
└── server/
    ├── pyproject.toml     # Python project config
    └── src/kg_mcp/
        ├── main.py        # Server entry point
        ├── config.py      # Settings management
        ├── cli/           # CLI commands
        │   └── setup.py   # Setup wizard
        ├── llm/           # LLM integration
        │   ├── client.py  # LiteLLM wrapper
        │   └── prompts/   # Prompt templates
        ├── kg/            # Knowledge graph
        │   ├── neo4j.py   # Driver
        │   ├── repo.py    # Query repository
        │   ├── ingest.py  # Ingestion pipeline
        │   └── retrieval.py # Context builder
        ├── mcp/           # MCP components
        │   ├── tools.py   # Tool definitions
        │   ├── resources.py # Resource handlers
        │   └── prompts.py # Prompt templates
        └── security/      # Auth & validation
```

### Code Style

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/your-org/mcp-kg-memory.git
cd mcp-kg-memory/server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/mcp-kg-memory/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/mcp-kg-memory/discussions)

---

<div align="center">

Made with ❤️ for AI-assisted development

</div>
