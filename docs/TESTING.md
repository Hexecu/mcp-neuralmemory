# Comprehensive Testing & Verification Suite

Neural Memory uses an exhaustive multi-layer testing pipeline to verify stability, mathematical correctness of the physics engine, memory safety under extreme scale, privacy masking integrity, and standalone MacBook portability.

---

## 1. Test Batteries Overview

| Target | Command | Description | Duration |
| :--- | :--- | :--- | :--- |
| **Full Massive Battery** | `make test-massive` | 5-stage comprehensive stress, chaos, scale & UI E2E suite | ~45s |
| **Standalone Clean Sim** | `make verify-clean` | Isolated MacBook simulation with zero Docker | ~5s |
| **Python Unit & Chaos** | `make test` | 74 unit, fuzzing, and SQLite property graph tests | ~2s |
| **Swift Scale & UI** | `cd apps/macos && swift test` | 15 contract, 500-node physics, and layout tests | ~22s |
| **Open Local Doctor** | `make doctor` | 6-point verification of Docker, API, and Neo4j stack | ~1s |
| **Integration E2E** | `make e2e` | 9-point end-to-end API and MCP handshake tests | ~5s |

---

## 2. The 5-Stage Massive Test Battery (`make test-massive`)

### Stage 1: Python Unit & Chaos Fuzzing Suite
Runs `pytest` across all backend services in `server/tests/`:
- **Chaos Fuzzing (`test_chaos_fuzzing.py`)**: Tests high-entropy randomized inputs, Unicode injections, null-byte attacks (`\x00`), and truncated JSON payloads.
- **PrivacyShield Fuzzing**: Verifies 100% masking of sensitive patterns (OpenAI `sk-...`, Gemini `AIza...`, GitHub tokens, Visa/Mastercard with Luhn checksums, IBAN numbers).
- **SQLite Property Graph Store (`test_sqlite_store.py`)**: Verifies embedded standalone storage, raw events, activity slices, node upserts, temporal filtering (`since`/`until`), and full-text search.

### Stage 2: Swift Scale, 500-Node Physics & UI Contracts
Runs XCTest suite in `apps/macos/Tests/`:
- **Massive 500-Node Simulation (`ScaleAndResilienceTests.swift`)**:
  - Simulates 500 nodes and 1,200 interconnecting edges under continuous physics iterations.
  - Asserts zero `NaN`, zero `+Inf`/`-Inf`, and validates velocity clamping ($[-30, 30]$).
  - Validates spatial Manhattan pre-filtering ($|dx| > 280$) achieving sub-millisecond step execution.
- **UI & Geometry Contracts (`UIGraphicalE2ETests.swift`)**:
  - Validates semantic color hex mappings.
  - Verifies Timeline Stream vertical altitude lane coordinates.
  - Verifies node hit-testing and neighbor jump navigation.

### Stage 3: High-Concurrency & Load Benchmark (`massive_stress_test.py`)
Stress-tests the ingestion daemon under intense concurrent write traffic:
- **Throughput Benchmark**: Spawns 30 concurrent asynchronous workers sending 100 distinct interaction events.
  - Benchmark result: **400.7 requests/second** ($p_{50} = 18.41\text{ ms}$, $p_{95} = 117.86\text{ ms}$).
- **Screenshot Deduplication Stress**: Ingests visual frames at **14.1 screenshots/second**, verifying that identical visual frames are caught and deduplicated via perceptual `dhash`.
- **Concurrent Mixed Workload**: Interleaves simultaneous writes with search queries and a background **Dream Mode consolidation cycle** with zero deadlocks.

### Stage 4: Graphical & UI Window Hierarchy E2E (`verify_ui_graphics.py`)
Inspects the live macOS window server via `CGWindowListCopyWindowInfo`:
- Verifies native window geometry (1050x720 px, Layer 0, `kCGWindowIsOnscreen = true`).
- Verifies the HTML5 / SVG / D3 embedded graph visualizer page renders valid interactive DOM elements.

### Stage 5: Core Integration E2E (`scripts/test-e2e.sh`)
End-to-end verification of:
1. Health check identity (`GET /health`).
2. Authentication enforcement (401 on missing token, 403 on invalid token).
3. Raw activity event ingestion with Bearer token.
4. Perceptual visual hash generation and deduplication.
5. Activity slice creation and linking.
6. Deep hybrid search.
7. MCP stdio protocol initialization and JSON-RPC handshake.

---

## 3. Standalone Clean Environment Simulation (`make verify-clean`)

Simulates running on a virgin MacBook with **no developer tools, no Python, and Docker shut down**:
1. Shuts down Docker Compose (`docker compose down`).
2. Purges development environment variables and runs with isolated system `PATH` (`/usr/bin:/bin:/usr/sbin:/sbin`).
3. Launches the standalone Mach-O binary `dist/NeuralMemoryAgent.app/Contents/MacOS/neural-memory-daemon`.
4. Polls `/health` until ready.
5. Verifies active storage mode is `"embedded_sqlite"`.
6. Sends an authenticated event using the local token file `~/Library/Application Support/NeuralMemory/token.txt`.
7. Queries the graph structure via `/api/graph/data`.
8. Asserts that the physical database file `~/Library/Application Support/NeuralMemory/memory.db` was created and populated.
