# Contributing

Thanks for helping make personal AI memory more reliable and understandable.

Before opening a pull request, describe the user-visible problem and keep the change focused. Privacy-affecting behavior needs an explicit opt-in and documentation update.

Run the relevant checks:

```bash
cd server
python -m pytest -q
ruff check src/kg_mcp/api.py src/kg_mcp/config.py src/kg_mcp/main.py tests/test_api.py tests/test_scoring.py

cd ../apps/macos
swift build
```

For backend behavior, add a regression test that fails before the fix and passes after it. Never use real screenshots, browsing history, typed text, credentials or exported graph data as fixtures. Synthetic examples should be obviously fictional.

Pull requests should state what changed, why it changed, how it was verified and any limitation that remains.
