# Standalone Installer Guide (Zero-Prerequisites / Zero-Docker)

Neural Memory provides an enterprise-ready, standalone **Drag-and-Drop macOS DMG Installer** designed to run on any MacBook running macOS 13 (Ventura) or later, requiring **no Docker, no Python, no Homebrew, and no terminal commands**.

---

## 1. Quick Installation for End Users

1. **Download / Obtain the Installer**:
   - File: `NeuralMemoryAgent-0.2.0-Installer.dmg` (approx. 112 MB).
2. **Mount the Disk Image**:
   - Double-click `NeuralMemoryAgent-0.2.0-Installer.dmg`.
   - A window will appear showing `NeuralMemoryAgent.app` and a shortcut to `/Applications`.
3. **Install**:
   - Drag `NeuralMemoryAgent.app` into the **Applications** folder.
4. **Launch**:
   - Open **Applications** -> **NeuralMemoryAgent**.
   - *First launch notice*: If macOS Gatekeeper presents an unidentified developer warning, right-click (or Control-click) `NeuralMemoryAgent.app` and choose **Open**, then click **Open** in the confirmation dialog.
5. **Ready to Go!**:
   - The app icon will appear in your macOS menu bar (top-right).
   - An embedded background daemon starts automatically in under 0.2 seconds.
   - A private local database is initialized at:
     `~/Library/Application Support/NeuralMemory/memory.db`.

---

## 2. macOS System Permissions Setup

To enable contextual memory assistance, Neural Memory requests standard macOS privacy permissions. Both are managed in **System Settings -> Privacy & Security**:

| Permission | Reason for Request | Where to Configure |
| :--- | :--- | :--- |
| **Accessibility** | Required to identify the active application name and window title. | *System Settings > Privacy & Security > Accessibility* -> Enable **NeuralMemoryAgent** |
| **Screen Recording** | *(Optional)* Required only if you enable Visual Context (screenshot capture). | *System Settings > Privacy & Security > Screen Recording* -> Enable **NeuralMemoryAgent** |

> [!NOTE]
> All capture starts in **Disabled / Paused** state by default. Neural Memory never captures any screen or text without your explicit consent.

---

## 3. How Standalone Mode Works Under the Hood

When you run `NeuralMemoryAgent.app` without Docker installed:

1. **Embedded Child Daemon**:
   The native Swift application bundles a compiled Mach-O universal binary (`neural-memory-daemon`) compiled with PyInstaller.
   `EmbeddedDaemonManager.swift` starts this daemon automatically as a background child process listening on `http://127.0.0.1:8765`.
2. **Embedded SQLite Property Graph Engine**:
   Instead of requiring a heavy Neo4j JVM cluster, the daemon automatically activates `use_embedded = True`, routing all knowledge graph operations to a high-speed SQLite database in WAL (Write-Ahead Logging) mode.
3. **Zero-Configuration Token Management**:
   The daemon generates a secure 256-bit token saved at `~/Library/Application Support/NeuralMemory/token.txt`. The Swift client automatically detects and uses this token to authenticate all requests.
4. **Clean Termination**:
   When you quit Neural Memory from the menu bar or dock, `EmbeddedDaemonManager` cleanly sends `SIGTERM` to the daemon, ensuring zero orphan processes remain.

---

## 4. Building the Installer from Source (`make package`)

If you are a developer compiling the release DMG from the source repository:

### Prerequisites
- macOS 13+ with Xcode Command Line Tools (`xcode-select --install`).
- Python 3.11+ with PyInstaller 6.x installed in `server/.venv`.

### Build Command
```bash
make package
```

### What `make package` Executes
1. Cleans the `dist/` directory.
2. Compiles the native Swift UI in Release configuration (`swift build -c release`).
3. Compiles the standalone Python daemon Mach-O binary using PyInstaller:
   ```bash
   server/.venv/bin/pyinstaller --clean -y \
     --name neural-memory-daemon \
     --add-data "server/src/kg_mcp/web/graph.html:kg_mcp/web" \
     --paths server/src \
     server/src/kg_mcp/daemon_entry.py
   ```
4. Generates standard macOS multi-resolution ICNS icon (`AppIcon.icns`).
5. Assembles `dist/NeuralMemoryAgent.app` bundle and signs with ad-hoc signature (`codesign -s -`).
6. Creates the compressed disk image `dist/NeuralMemoryAgent-0.2.0-Installer.dmg` with `hdiutil`.

---

## 5. Simulating a Clean MacBook (`make verify-clean`)

To verify that the application operates properly on a virgin MacBook with no developer tools or Docker installed:

```bash
make verify-clean
```

The script performs the following automated tests:
1. Shuts down Docker Compose completely (`docker compose down`).
2. Isolates the shell environment with a minimal system `PATH` (`/usr/bin:/bin:/usr/sbin:/sbin`), stripping any Homebrew or Conda binaries.
3. Executes the standalone daemon Mach-O binary.
4. Verifies `http://127.0.0.1:8795/health` responds with `{"status":"ok"}`.
5. Verifies `/api/config` reports `"storage_mode": "embedded_sqlite"`.
6. Sends an authenticated test activity event (`/api/ingest/event`).
7. Queries the graph structure (`/api/graph/data`).
8. Verifies the physical creation of `~/Library/Application Support/NeuralMemory/memory.db`.
9. Terminates the process cleanly.

---

## 6. Logs & Troubleshooting

| Purpose | File Location |
| :--- | :--- |
| **Daemon Console & Error Log** | `~/Library/Logs/NeuralMemoryAgent/daemon.log` |
| **Embedded Graph Database** | `~/Library/Application Support/NeuralMemory/memory.db` |
| **Authentication Token** | `~/Library/Application Support/NeuralMemory/token.txt` |

### Common Issues

- **Daemon fails to bind to port 8765**:
  - Another service or container is using port 8765. Run `lsof -i :8765` to find the process ID.
  - If Docker is running, Neural Memory will automatically connect to it instead of starting the embedded daemon.
- **Connection status shows "Daemon unreachable"**:
  - Check `~/Library/Logs/NeuralMemoryAgent/daemon.log` for error messages.
  - Open **Settings** -> **Server** tab and click **Test Connection**.
- **Resetting Database**:
  - To wipe local memory and start fresh:
    ```bash
    rm -f ~/Library/Application\ Support/NeuralMemory/memory.db*
    ```
