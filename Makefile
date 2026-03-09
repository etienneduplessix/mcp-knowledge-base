.PHONY: help install test run docker-build docker-run docker-test clean

# Default target
help:
	@echo "MCP Knowledge Base Server - Available Commands"
	@echo ""
	@echo "Local Development:"
	@echo "  make install       Install dependencies"
	@echo "  make test          Run test suite"
	@echo "  make run           Run the server locally"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-run    Run with Docker Compose"
	@echo "  make docker-test   Run tests in Docker"
	@echo "  make docker-stop   Stop Docker containers"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean         Clean up generated files"
	@echo "  make fmt           Format code with black"
	@echo "  make lint          Lint code with ruff"

# Local development
install:
	pip install -r requirements.txt

test:
	python test_kb.py

run:
	python mcp_kb_server.py

# Docker commands
docker-build:
	docker build -t mcp-kb-server .

docker-run:
	docker-compose up -d

docker-test:
	docker-compose --profile testing run --rm test

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Development with hot-reload
docker-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Maintenance
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/

fmt:
	black *.py

lint:
	ruff check *.py

# All checks
check: test lint
	@echo "All checks passed!"
