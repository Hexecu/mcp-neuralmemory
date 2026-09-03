# Neural Memory for macOS

This preview client can send app and window context to a Neural Memory server running on the same machine. Collection is disabled on a fresh install.

## Build an app bundle

```bash
./bundle_app.sh
open NeuralMemoryAgent.app
```

Requirements are macOS 13 or later and Xcode Command Line Tools. The generated development bundle is unsigned and intended for local testing.

## Connect it

1. Start the root Docker stack with `../../scripts/bootstrap.sh`.
2. Open the app's Settings.
3. Keep the server URL at `http://127.0.0.1:8765` unless you changed the local port.
4. Copy `KG_MCP_TOKEN` from the root `.env` into the API token field.
5. Test the connection.
6. Enable only the capture types you want.

Activity capture, screenshots and typed text are independent choices. Private Mode and Pause Capture are available from the menu bar. Read the root [privacy model](../../docs/PRIVACY.md) before enabling screenshot or typed-text capture.

The release path still needs Developer ID signing, notarization and a packaged installer. Those are not implied by this development bundle.
