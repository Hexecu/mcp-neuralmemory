.PHONY: help setup up down logs doctor test lint macos

help:
	@echo "Neural Memory"
	@echo "  make setup   Generate local credentials and start the stack"
	@echo "  make doctor  Check the local installation"
	@echo "  make test    Run backend regression tests"
	@echo "  make macos   Build the native macOS client"
	@echo "  make down    Stop the stack without deleting your graph"

setup:
	./scripts/bootstrap.sh

up:
	docker compose up --detach

down:
	docker compose down

logs:
	docker compose logs --follow api neo4j

doctor:
	./scripts/doctor.sh

test:
	cd server && python -m pytest -q

lint:
	cd server && ruff check src/kg_mcp/api.py src/kg_mcp/config.py src/kg_mcp/main.py src/kg_mcp/image_hash.py src/kg_mcp/mcp/life_tools.py tests/test_api.py tests/test_scoring.py

macos:
	cd apps/macos && ./bundle_app.sh
