import os
import sys
from pathlib import Path

support_dir = Path.home() / "Library" / "Application Support" / "NeuralMemory"
support_dir.mkdir(parents=True, exist_ok=True)
token_file = support_dir / "token.txt"

if not os.environ.get("KG_MCP_TOKEN"):
    if token_file.exists():
        os.environ["KG_MCP_TOKEN"] = token_file.read_text().strip()
    else:
        import secrets
        token = secrets.token_hex(32)
        token_file.write_text(token)
        os.environ["KG_MCP_TOKEN"] = token

import argparse
from kg_mcp.main import run_http

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neural Memory Standalone Daemon")
    parser.add_argument("--host", default=os.environ.get("NEURAL_MEMORY_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("NEURAL_MEMORY_PORT", "8765")))
    args, _ = parser.parse_known_args()
    run_http(host=args.host, port=args.port)
