# Model Context Protocol (MCP) Tools Reference

Neural Memory provides an AI-native interface compliant with the **Model Context Protocol (MCP)** specification. This enables external AI agents (such as Claude Desktop, Cursor, Google Antigravity, and custom agent workflows) to autonomously query and reinforce your cognitive second brain.

---

## 1. Tool Categories & Schemas

### 1.1 Life & Personal Cognitive Tools

#### `recall_decisions`
Retrieves past strategic decisions, approvals, and rejections made by you or your team.
- **Arguments**:
  - `topic` *(optional, string)*: Filter decisions by specific topic keyword (e.g. `"Cloud Q4"`).
  - `person` *(optional, string)*: Filter decisions involving a specific person (e.g. `"Marco Rossi"`).
  - `project_id` *(optional, string, default: `"default"`)*: Project namespace.
  - `limit` *(optional, integer, default: `10`)*: Maximum results to return.
- **Example Response**:
  ```json
  [
    {
      "id": "d-a812f0c1",
      "title": "Approve Cloud Q4 Quote for 5000 EUR",
      "verdict": "APPROVED",
      "rationale": "User typed 'Ok procedi pure' in response to quote email",
      "timestamp": "2026-09-03T14:10:00Z",
      "person": "Marco Rossi"
    }
  ]
  ```

#### `recall_commitments`
Retrieves action items, deliverables, and promises with explicit deadlines and responsible parties.
- **Arguments**:
  - `status` *(optional, string, default: `"open"`)*: Filter by status (`"open"`, `"in_progress"`, `"completed"`).
  - `debtor` *(optional, string)*: Who owes the deliverable (`"user"` or colleague name).
  - `creditor` *(optional, string)*: Who is expecting delivery.
  - `limit` *(optional, integer, default: `10`)*: Maximum items.
- **Example Response**:
  ```json
  [
    {
      "id": "c-4b9981e2",
      "title": "Send updated slides by Friday 18:00",
      "due_date": "2026-09-05T18:00:00Z",
      "status": "open",
      "debtor": "user",
      "creditor": "Giulia Bianchi"
    }
  ]
  ```

#### `recall_meetings`
Retrieves summaries of collaborative video calls, meetings, and participant discussions.
- **Arguments**:
  - `topic` *(optional, string)*: Keyword search in meeting agendas or summaries.
  - `attendee` *(optional, string)*: Colleague name who participated.
  - `limit` *(optional, integer, default: `5`)*.
- **Example Response**:
  ```json
  [
    {
      "title": "Architecture Sync with Roberto & Francesca",
      "start_time": "2026-09-03T10:00:00Z",
      "attendees": ["Francesca", "Roberto"],
      "summary": "Agreed to adopt hybrid SQLite standalone alongside Neo4j."
    }
  ]
  ```

#### `get_daily_briefing`
Generates an executive briefing summarizing all decisions, open commitments, and meetings for a target date.
- **Arguments**:
  - `date` *(optional, string, ISO format: `YYYY-MM-DD`)*: Target day (defaults to today).
  - `project_id` *(optional, string, default: `"default"`)*.

---

### 1.2 Project & Code Memory Tools

#### `search`
Performs deep hybrid search (full-text and graph neighborhood traversal) over the entire knowledge base.
- **Arguments**:
  - `query` *(required, string)*: Semantic search prompt.
  - `limit` *(optional, integer, default: `10`)*.
  - `project_id` *(optional, string, default: `"default"`)*.

#### `get_project_context`
Returns the aggregated active working context, recent activity slices, and concepts for a given project.
- **Arguments**:
  - `project_id` *(required, string)*: Target project identifier.

---

## 2. Client Configuration Guides

### 2.1 Claude Desktop Integration
Add the following configuration to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "neural-memory": {
      "command": "/usr/local/bin/kg-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "NEO4J_URI": "bolt://127.0.0.1:8787",
        "NEO4J_PASSWORD": "your-neo4j-password-from-env"
      }
    }
  }
}
```

Or run the automated configuration helper:
```bash
./scripts/setup-mcp.sh --claude
```

### 2.2 Cursor & Antigravity IDE Integration
In Cursor settings under **MCP Servers** -> **Add New MCP Server**:
- **Name**: `neural-memory`
- **Type**: `command`
- **Command**: `kg-mcp --transport stdio`

---

## 3. Real-World Agent Interaction Example

**User to Claude Desktop**:
> *"Claude, what did I promise to send to Giulia Bianchi this week, and did we agree on any cloud pricing today?"*

**Claude Autonomous Tool Execution**:
1. Calls `recall_commitments(creditor="Giulia Bianchi", status="open")`
   $	o$ Returns: `"Send updated slides by Friday 18:00"`
2. Calls `recall_decisions(topic="Cloud", limit=5)`
   $	o$ Returns: `"Approved Cloud Q4 Quote for 5000 EUR towards Marco Rossi"`

**Claude Response**:
> *"You have an open commitment to send updated slides to **Giulia Bianchi** by **Friday, September 5 at 18:00**.*
> 
> *Regarding cloud pricing, earlier today you approved the **Cloud Q4 Quote for 5,000 EUR** communicated with Marco Rossi."*
