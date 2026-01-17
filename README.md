# MCP-KG-Memory

> **Memory/Knowledge Graph MCP Server** - Un server MCP che mantiene contesto persistente, preferenze, obiettivi e knowledge graph per assistenti AI negli IDE.

## 🎯 Funzionalità

- **Ingestion intelligente**: Analizza ogni richiesta utente ed estrae obiettivi, vincoli, preferenze, pain points e strategie usando Gemini 2.5
- **Context Pack**: Ad ogni richiesta, naviga il grafo e restituisce contesto rilevante per non perdere la rotta
- **Code Graph**: Mappa file → simboli → riferimenti/calls per impact analysis
- **Goal Tracking**: Obiettivo → codice → test per sapere cosa ritestare quando qualcosa cambia
- **Retrieval ibrido**: Traversal del grafo + fulltext search + (opzionale) embeddings

## 📋 Prerequisiti

- Python 3.11+
- Docker e Docker Compose
- Neo4j 5.x (fornito via Docker)
- API Key Gemini (Google AI Studio)

## 🚀 Quick Start

### 1. Setup ambiente

```bash
cd mcp-kg-memory

# Copia e configura le variabili d'ambiente
cp .env.example .env
# Edita .env con le tue API keys

# Crea virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# oppure: .venv\Scripts\activate  # Windows

# Installa dipendenze
cd server
pip install -e .
```

### 2. Avvia Neo4j

```bash
# Dalla root del progetto
docker-compose up -d neo4j

# Verifica che Neo4j sia up (attendi ~30s)
docker-compose logs -f neo4j
```

### 3. Applica schema Neo4j

```bash
# Una volta che Neo4j è pronto
python -m kg_mcp.kg.apply_schema
```

### 4. Avvia il server MCP

```bash
# Dalla cartella server

# Modalità HTTP (default) - per serverUrl config
python -m kg_mcp --transport http
# Il server sarà disponibile su http://127.0.0.1:8000/mcp

# Modalità STDIO - per command/args config  
python -m kg_mcp --transport stdio

# Con opzioni custom
python -m kg_mcp --transport http --host 0.0.0.0 --port 9000
```

## 🖥️ CLI Reference

Il server supporta due modalità di trasporto:

```bash
# STDIO mode (per Antigravity/IDE command config)
kg-mcp --transport stdio
python -m kg_mcp --transport stdio

# HTTP mode (per serverUrl config o standalone)
kg-mcp --transport http --host 127.0.0.1 --port 8000
python -m kg_mcp -t http -p 8000
```

**Opzioni:**
- `--transport`, `-t`: Modalità trasporto (`stdio` | `http`, default: `http`)
- `--host`: Host per HTTP mode (default: `127.0.0.1`)
- `--port`, `-p`: Porta per HTTP mode (default: `8000`)
- `--path`: Path endpoint MCP (default: `/mcp`)

## 🔧 Configurazione IDE

### VS Code

Crea/modifica `.vscode/mcp.json`:

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

Aggiungi in `~/.cursor/mcp.json`:

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

### Cline/Roo Code

Aggiungi in `.cline/mcp_config.json`:

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

### 🚀 Google Antigravity IDE

Antigravity supporta due modalità di configurazione MCP:

#### Setup Steps:
1. Apri **Agent sidebar** (o Agent Manager)
2. Clicca **...** (More Actions)
3. Seleziona **MCP Servers**
4. Vai su **Manage MCP Servers** → **View raw config** (apre `mcp_config.json`)
5. Incolla una delle configurazioni sotto
6. Salva il file e premi **Refresh**

#### Opzione A: Server Locale (command/args) ✅ Consigliato per dev

```json
{
  "mcpServers": {
    "kg-memory": {
      "command": "python",
      "args": ["-m", "kg_mcp", "--transport", "stdio"],
      "env": {
        "NEO4J_URI": "bolt://127.0.0.1:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your_password",
        "GEMINI_API_KEY": "your_gemini_key",
        "KG_MCP_TOKEN": "your_token"
      }
    }
  }
}
```

#### Opzione B: Server Remoto (serverUrl) ✅ Per produzione/cloud

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

> **Nota:** In modalità `command`, assicurati che Python e le dipendenze siano nel PATH.
> Puoi usare il path completo: `"command": "/path/to/.venv/bin/python"`

## 📚 MCP Tools

### `kg_ingest_message`
Analizza e salva una richiesta utente nel knowledge graph.

**Input:**
- `project_id`: ID del progetto
- `user_text`: Testo della richiesta utente
- `files` (opzionale): Lista di path file coinvolti
- `diff` (opzionale): Diff del codice
- `symbols` (opzionale): Lista di simboli
- `tags` (opzionale): Tag aggiuntivi

**Output:**
- `interaction_id`: ID dell'interazione creata
- `extracted`: JSON con entità estratte
- `created_entities`: IDs delle entità create

### `kg_context_pack`
Costruisce un context pack navigando il grafo.

**Input:**
- `project_id`: ID del progetto
- `focus_goal_id` (opzionale): ID goal su cui focalizzarsi
- `query` (opzionale): Query di ricerca
- `k_hops`: Numero di hop nel grafo (default: 2)

**Output:**
- `markdown`: Contesto formattato in Markdown
- `entities`: Lista di entità rilevanti

### `kg_search`
Cerca nel knowledge graph con fulltext + traversal.

**Input:**
- `project_id`: ID del progetto
- `query`: Query di ricerca
- `filters` (opzionale): Filtri per tipo entità
- `limit`: Limite risultati (default: 20)

### `kg_link_code_artifact`
Collega un artefatto di codice al grafo.

**Input:**
- `project_id`: ID del progetto
- `path`: Path del file
- `kind`: Tipo (file/function/class/snippet)
- `language`: Linguaggio
- `symbol_fqn` (opzionale): Fully qualified name del simbolo
- `start_line`, `end_line` (opzionale): Range linee
- `git_commit` (opzionale): Commit hash
- `content_hash` (opzionale): Hash del contenuto
- `related_goal_ids` (opzionale): IDs goal collegati

### `kg_impact_analysis`
Analizza l'impatto di modifiche al codice.

**Input:**
- `project_id`: ID del progetto
- `changed_paths`: Lista di path modificati
- `changed_symbols`: Lista di simboli modificati

**Output:**
- `goals_to_retest`: Goals che potrebbero essere impattati
- `tests_to_run`: Test da eseguire
- `strategies_to_review`: Strategie da rivedere
- `artifacts_related`: Artefatti correlati

## 📖 MCP Resources

- `kg://projects/{project_id}/active-goals` - Goals attivi del progetto
- `kg://projects/{project_id}/preferences` - Preferenze utente
- `kg://projects/{project_id}/goal/{goal_id}/subgraph` - Subgraph di un goal

## 💬 MCP Prompts

### `StartCodingWithKG`
Template che istruisce l'agente IDE a:
1. Chiamare `kg_ingest_message` con la richiesta utente
2. Chiamare `kg_context_pack` e usare quel markdown come contesto
3. Quando crea/modifica file, chiamare `kg_link_code_artifact`

## 🔒 Sicurezza

- Server bind su `127.0.0.1` (solo accessi locali)
- Autenticazione Bearer token obbligatoria
- Origin allowlist configurabile
- Nessuna esecuzione di comandi shell
- Audit log per ogni operazione

## 🏗️ Architettura

```
┌─────────────────────────────────────────────────────────────┐
│                        IDE Agent                             │
│  (VS Code/Cursor/Cline con MCP Client)                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ MCP (Streamable HTTP)
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
                          │ Bolt
                          ▼
              ┌───────────────────────┐
              │        Neo4j          │
              │  (Knowledge Graph)    │
              └───────────────────────┘
```

## 📜 License

MIT License

## 🤝 Contributing

PRs welcome! Per favore apri prima una issue per discutere le modifiche proposte.
