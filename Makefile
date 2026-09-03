.PHONY: help setup up down logs doctor test test-massive e2e lint macos package verify-clean mcp

help:
	@echo "Neural Memory"
	@echo "  make setup        Generate local credentials and start the stack"
	@echo "  make doctor       Check the local installation"
	@echo "  make test         Run backend regression tests"
	@echo "  make test-massive Run comprehensive massive stress, chaos, scale & UI E2E suite"
	@echo "  make package      Build standalone DMG installer (Zero Docker, Zero Prerequisites)"
	@echo "  make verify-clean Test standalone app in simulated clean environment"
	@echo "  make e2e          Run end-to-end integration tests"
	@echo "  make macos        Build the native macOS client"
	@echo "  make mcp          Configure MCP for Claude Desktop and Cursor"
	@echo "  make down         Stop the stack without deleting your graph"

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

test-massive:
	@echo "🔥 Running Massive Test Battery..."
	@echo "1/5. Python Unit & Chaos Fuzzing Suite"
	cd server && python -m pytest -q
	@echo "2/5. Swift Scale, 500-Node Physics & UI Contracts"
	cd apps/macos && swift test
	@echo "3/5. High-Throughput Concurrency & Load Benchmark"
	python3 ./scripts/massive_stress_test.py --concurrency 30 --events 100
	@echo "4/5. Graphical & UI Window Hierarchy E2E"
	python3 ./scripts/verify_ui_graphics.py
	@echo "5/5. End-to-End Core Integration Suite"
	./scripts/test-e2e.sh
	@echo "🎉 All Massive Tests & UI E2E Verifications Passed!"

e2e:
	./scripts/test-e2e.sh

lint:
	cd server && ruff check src/kg_mcp/api.py src/kg_mcp/config.py src/kg_mcp/main.py src/kg_mcp/image_hash.py src/kg_mcp/mcp/life_tools.py tests/test_api.py tests/test_scoring.py

package:
	./scripts/package_installer.sh

verify-clean:
	./scripts/verify_clean_environment.sh

macos:
	cd apps/macos && ./bundle_app.sh

mcp:
	./scripts/setup-mcp.sh
