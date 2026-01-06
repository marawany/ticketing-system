# NexusFlow Makefile
# ============================================================================

.PHONY: help install dev setup run api mcp frontend all test lint clean docker-build docker-up docker-down

# Default target
help:
	@echo "NexusFlow - Intelligent Ticket Classification System"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  install       Install production dependencies"
	@echo "  dev           Install development dependencies"
	@echo "  setup         Setup databases and generate synthetic data"
	@echo ""
	@echo "Run Services:"
	@echo "  api           Start FastAPI server (port 8000)"
	@echo "  mcp           Start MCP server (port 8001)"
	@echo "  frontend      Start Next.js frontend (port 3000)"
	@echo "  phoenix       Start Arize Phoenix (port 6006)"
	@echo "  all           Start all services (api, mcp, phoenix)"
	@echo ""
	@echo "Testing:"
	@echo "  test          Run all tests"
	@echo "  test-api      Run API integration tests"
	@echo "  test-unit     Run unit tests"
	@echo "  lint          Run linting"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  Build Docker images"
	@echo "  docker-up     Start all services with Docker Compose"
	@echo "  docker-down   Stop all Docker services"
	@echo ""
	@echo "Utilities:"
	@echo "  clean         Clean generated files"
	@echo "  generate      Generate synthetic data"
	@echo "  db-setup      Setup Neo4j and Milvus"

# ============================================================================
# Setup & Installation
# ============================================================================

install:
	@echo "Installing dependencies..."
	uv venv
	. .venv/bin/activate && uv pip install -e .

dev:
	@echo "Installing development dependencies..."
	uv venv
	. .venv/bin/activate && uv pip install -e ".[dev]"

setup: generate db-setup
	@echo "Setup complete!"

generate:
	@echo "Generating synthetic data..."
	. .venv/bin/activate && python scripts/generate_synthetic_data.py

db-setup:
	@echo "Setting up databases..."
	. .venv/bin/activate && python scripts/setup_databases.py

# ============================================================================
# Run Services
# ============================================================================

api:
	@echo "Starting FastAPI server on port 8000..."
	. .venv/bin/activate && uvicorn nexusflow.api.main:app --host 0.0.0.0 --port 8000 --reload

mcp:
	@echo "Starting MCP server on port 8001..."
	. .venv/bin/activate && python -m nexusflow.mcp.server

frontend:
	@echo "Starting Next.js frontend on port 3000..."
	cd frontend && npm run dev

phoenix:
	@echo "Starting Arize Phoenix on port 6006..."
	docker run -d --name nexusflow-phoenix -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest

all:
	@echo "Starting all services..."
	@make -j3 api mcp phoenix

# Background service runners
api-bg:
	@echo "Starting FastAPI server in background..."
	. .venv/bin/activate && nohup uvicorn nexusflow.api.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
	@echo "API server started (logs: logs/api.log)"

mcp-bg:
	@echo "Starting MCP server in background..."
	. .venv/bin/activate && nohup python -m nexusflow.mcp.server > logs/mcp.log 2>&1 &
	@echo "MCP server started (logs: logs/mcp.log)"

start-all: 
	@mkdir -p logs
	@make api-bg
	@make mcp-bg
	@echo ""
	@echo "All services started!"
	@echo "  API: http://localhost:8000"
	@echo "  MCP: http://localhost:8001"
	@echo "  Docs: http://localhost:8000/docs"

stop-all:
	@echo "Stopping all services..."
	-pkill -f "uvicorn nexusflow"
	-pkill -f "nexusflow.mcp.server"
	@echo "All services stopped"

# ============================================================================
# Testing
# ============================================================================

test: test-unit test-api
	@echo "All tests completed!"

test-unit:
	@echo "Running unit tests..."
	. .venv/bin/activate && pytest tests/ -v --tb=short

test-api:
	@echo "Running API integration tests..."
	. .venv/bin/activate && python scripts/test_api.py

test-cov:
	@echo "Running tests with coverage..."
	. .venv/bin/activate && pytest tests/ --cov=nexusflow --cov-report=html --cov-report=term

lint:
	@echo "Running linting..."
	. .venv/bin/activate && ruff check src/ tests/
	. .venv/bin/activate && ruff format --check src/ tests/

format:
	@echo "Formatting code..."
	. .venv/bin/activate && ruff format src/ tests/
	. .venv/bin/activate && ruff check --fix src/ tests/

typecheck:
	@echo "Running type checking..."
	. .venv/bin/activate && mypy src/nexusflow

# ============================================================================
# Docker
# ============================================================================

docker-build:
	@echo "Building Docker images..."
	docker compose build

docker-up:
	@echo "Starting Docker services..."
	docker compose up -d

docker-up-local:
	@echo "Starting Docker services with local databases..."
	docker compose --profile local-dbs up -d

docker-down:
	@echo "Stopping Docker services..."
	docker compose down

docker-logs:
	docker compose logs -f

docker-ps:
	docker compose ps

# ============================================================================
# Utilities
# ============================================================================

clean:
	@echo "Cleaning generated files..."
	rm -rf .venv
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf *.egg-info
	rm -rf logs/*.log
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

logs:
	@mkdir -p logs
	@echo "Logs directory ready"

# Quick health check
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "API not running"
	@curl -s http://localhost:8000/health/ready | python -m json.tool || echo "API not ready"

# Show stats
stats:
	@echo "Getting system stats..."
	. .venv/bin/activate && python -c "from nexusflow.cli import stats; import asyncio; asyncio.run(stats())"

