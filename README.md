# 🧠 Neural Memory

[![Platform](https://img.shields.io/badge/platform-macOS%2013%2B-blue.svg)](apps/macos)
[![Architecture](https://img.shields.io/badge/architecture-Dual--Track%20(Standalone%20%7C%20Docker)-success.svg)](docs/ARCHITECTURE.md)
[![Tests](https://img.shields.io/badge/tests-74%20Python%20%7C%2015%20Swift%20PASS-brightgreen.svg)](docs/TESTING.md)
[![Zero-Docker](https://img.shields.io/badge/standalone-Zero%20Docker%20Required-orange.svg)](docs/STANDALONE_INSTALLER.md)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

**Neural Memory** is a local-first personal cognitive memory assistant and second brain. It turns the desktop context you choose to share into an autonomous, searchable knowledge graph — anchoring real-world micro-feedback (like an *"Ok"* to an email quote), tracking commitments and decisions, and exposing your context directly to AI tools via the **Model Context Protocol (MCP)**.

---

## ⚡ Quick Start: Choose Your Track

Neural Memory offers a **Dual-Track Architecture** designed for both casual MacBook users and developer power users:

### Track B: Standalone Packed Installer (Recommended for Users)
> **Zero prerequisites. No Docker, no Python, no Homebrew, no terminal commands.**

1. Download **`NeuralMemoryAgent-0.2.0-Installer.dmg`** (approx. 112 MB).
2. Open the disk image and drag **`NeuralMemoryAgent.app`** to your **Applications** folder.
3. Launch the app from Applications.
   - Starts an embedded native daemon in under 0.2 seconds.
   - Stores all data locally in `~/Library/Application Support/NeuralMemory/memory.db`.
   - Access the menu bar icon, temporal graph, and settings instantly.
   - *Full guide: [docs/STANDALONE_INSTALLER.md](docs/STANDALONE_INSTALLER.md)*.

### Track A: Open Local Development Stack (For Developers)
> **Full Docker Compose + Neo4j 5.26 Community Graph Database.**

```bash
git clone https://github.com/Hexecu/mcp-neuralmemory.git
cd mcp-neuralmemory
./scripts/bootstrap.sh
```

- Verifies installation: `./scripts/doctor.sh`
- Graph API: `http://127.0.0.1:8765/health`
- Neo4j Browser: `http://127.0.0.1:8774` (User: `neo4j`, Password in `.env`)
- Stop without losing data: `make down`
- Re-start: `make up`

---

## 🌟 Why Neural Memory is Different

- 🔒 **PrivacyShield Redaction**: In-memory regex and Luhn checksum filtering automatically masks credit cards, IBANs, API keys (`sk-...`, `AIza...`, GitHub tokens), and ignores password vaults (`1Password`, `Bitwarden`, `Keychain`).
- 🎯 **Contextual Micro-Feedback Anchoring**: Eliminates arbitrary length cutoffs. When you type *"Ok, proceed with the 5,000 EUR quote"*, vision analysis anchors your consent directly to the sender, amount, and proposal document.
- 🌌 **Temporal Knowledge Graph**:
  - **Regional Topic Clusters**: Orbital regional gravity organizes entities into clean thematic galaxies without central collapse.
  - **Timeline Stream**: Horizontal chronological layout with 5 semantic altitude lanes (*Reflections*, *Decisions*, *Meetings*, *Commitments*, *Topics*).
  - **Time-Travel Scrubber**: Interactive slider to replay memory history with Ebbinghaus memory decay ($R = e^{-\Delta t / S}$).
- 🤖 **Agent-Ready Memory (MCP)**: Native Model Context Protocol server over `stdio` lets Claude Desktop, Cursor, Antigravity, and OpenCode recall past decisions, open commitments, and meeting notes.
- 🌙 **Cognitive Dream Mode**: Periodically prunes ephemeral low-level events (48h retention) and derives higher-order reflections and daily executive briefings.

---

## 📚 Complete Documentation Sitemap

| Guide | Description |
| :--- | :--- |
| **[System Architecture](docs/ARCHITECTURE.md)** | Deep technical dive into the Dual-Track execution model, data pipelines, and storage engines. |
| **[Standalone Installer Guide](docs/STANDALONE_INSTALLER.md)** | Step-by-step installation, permissions setup, and clean-environment testing on macOS. |
| **[Temporal Knowledge Graph](docs/TEMPORAL_GRAPH.md)** | Orbital physics model, semantic altitude lanes, time scrubber, and Ebbinghaus decay. |
| **[Cognitive Ontology](docs/ONTOLOGY.md)** | Entity schemas (`Decision`, `Commitment`, `Meeting`, `Reflection`), relationship semantics, and queries. |
| **[Model Context Protocol (MCP)](docs/MCP_TOOLS.md)** | Tool schemas (`recall_decisions`, `recall_commitments`, etc.) and configuration for Claude & Cursor. |
| **[Privacy Model & PrivacyShield](docs/PRIVACY.md)** | Data flow guarantees, deny-lists, masking algorithms, and ephemeral event pruning. |
| **[Testing & Verification](docs/TESTING.md)** | The 5-stage massive test battery (`make test-massive`) and clean simulation (`make verify-clean`). |

---

## 🤖 Connect to AI Agents (Claude Desktop & Cursor)

Neural Memory exposes your second brain directly to AI assistants:

```bash
# Auto-configure Claude Desktop:
./scripts/setup-mcp.sh --claude
```

### Available MCP Tools for Agents:
- `recall_decisions(topic, person)`: Recalls past strategic agreements and approvals.
- `recall_commitments(status, debtor, creditor)`: Recalls deliverables, action items, and deadlines.
- `recall_meetings(topic, attendee)`: Recalls discussion points and participants from calls.
- `get_daily_briefing(date)`: Generates an executive summary of the day.
- `search(query)`: Deep hybrid search across your accumulated memory graph.

*Example conversation*:
> **User**: *"Claude, what did I agree to send to Marco this Friday?"*  
> **Claude**: *"According to your Neural Memory, you committed to send the updated Cloud proposal slides to Marco Rossi by Friday at 18:00."*

---

## 🛠️ Developer & Makefile Commands

```bash
make help          # Show all available commands
make package       # Build the standalone macOS DMG installer (Zero Docker required)
make verify-clean  # Verify the standalone app in a clean, isolated MacBook simulation
make test-massive  # Run the full 5-stage massive stress, scale, chaos & UI test suite
make test          # Run Python unit & chaos tests (74 tests)
make e2e           # Run end-to-end API integration tests (9 tests)
make doctor        # Verify Docker, API, and Neo4j health
make lint          # Run ruff linter
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
