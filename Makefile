# MCP-KG-Memory Makefile
# Quick commands for development and deployment

.PHONY: help install setup dev test lint format clean neo4j-up neo4j-down schema server

# Default target
help:
	@echo "MCP-KG-Memory Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install     - Install dependencies"
	@echo "  make setup       - Run interactive setup wizard"
	@echo "  make dev         - Install with dev dependencies"
	@echo ""
	@echo "Database:"
	@echo "  make neo4j-up    - Start Neo4j container"
	@echo "  make neo4j-down  - Stop Neo4j container"
	@echo "  make schema      - Apply Neo4j schema"
	@echo ""
	@echo "Server:"
	@echo "  make server      - Run MCP server (HTTP mode)"
	@echo "  make server-stdio - Run MCP server (STDIO mode)"
	@echo ""
	@echo "Development:"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linter"
	@echo "  make format      - Format code"
	@echo "  make clean       - Clean build artifacts"

# Installation
install:
	cd server && python -m venv .venv && \
	. .venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -e .

dev:
	cd server && python -m venv .venv && \
	. .venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -e ".[dev]"

setup:
	cd server && . .venv/bin/activate && kg-mcp-setup

# Database commands
neo4j-up:
	docker compose up -d neo4j
	@echo "Waiting for Neo4j to be ready..."
	@sleep 15
	@echo "Neo4j should be ready at http://localhost:7474"

neo4j-down:
	docker compose down

neo4j-logs:
	docker compose logs -f neo4j

schema:
	cd server && . .venv/bin/activate && python -m kg_mcp.kg.apply_schema

# Server commands
server:
	cd server && . .venv/bin/activate && kg-mcp --transport http

server-stdio:
	cd server && . .venv/bin/activate && kg-mcp --transport stdio

# Development commands
test:
	cd server && . .venv/bin/activate && pytest tests/ -v

test-cov:
	cd server && . .venv/bin/activate && pytest tests/ --cov=kg_mcp --cov-report=html

lint:
	cd server && . .venv/bin/activate && ruff check src/ tests/

format:
	cd server && . .venv/bin/activate && black src/ tests/

typecheck:
	cd server && . .venv/bin/activate && mypy src/

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf server/htmlcov server/.coverage 2>/dev/null || true

# Full development setup
full-setup: install neo4j-up
	@sleep 20
	$(MAKE) schema
	@echo ""
	@echo "✓ Full setup complete!"
	@echo "Run 'make server' to start the MCP server"
