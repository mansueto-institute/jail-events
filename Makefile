# Makefile for Jail Events Processing Pipeline

.PHONY: help build up down clean full-pipeline sample-pipeline debug-pipeline handwritten-pipeline install-deps

# Default target
help:
	@echo "Available commands:"
	@echo "  build              - Build Docker image"
	@echo "  up                 - Start services"
	@echo "  down               - Stop services"
	@echo "  clean              - Clean up containers and images"
	@echo "  full-pipeline      - Run full pipeline on all data"
	@echo "  sample-pipeline    - Run pipeline on sample data"
	@echo "  debug-pipeline     - Run pipeline on debug data"
	@echo "  handwritten-pipeline - Run handwritten analysis only"
	@echo "  handwritten-smart    - Smart handwritten analysis (checks cache, runs full pipeline if needed)"
	@echo "  install-deps       - Install Python dependencies locally"
	@echo "  test               - Run tests"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

clean:
	docker-compose down --rmi all --volumes --remove-orphans

# Pipeline commands
full-pipeline:
	docker-compose run --rm pipeline

sample-pipeline:
	docker-compose run --rm jail-events uv run python src/jail-events/main.py --mode sample --step all

debug-pipeline:
	docker-compose run --rm jail-events uv run python src/jail-events/main.py --mode debug --step all

handwritten-pipeline:
	docker-compose run --rm handwritten

# Handwritten analysis using cached cleaned data (much faster)
handwritten-cached:
	docker-compose run --rm jail-events uv run python src/jail-events/main.py --mode handwritten --step handwritten

# Smart handwritten analysis (checks cache and runs full pipeline if needed)
handwritten-smart:
	docker-compose run --rm jail-events uv run --no-sync python src/jail-events/main.py --mode handwritten --step handwritten

# Local development
install-deps:
	pip install uv
	uv sync

# Testing
test:
	docker-compose run --rm jail-events uv run python -m pytest tests/

# Data management
create-handwritten-dir:
	mkdir -p src/jail-events/data/jails-data/handwritten_party

# Quick commands for common tasks
parse-only:
	docker-compose run --rm jail-events uv run python src/jail-events/main.py --mode full --step parse

clean-only:
	docker-compose run --rm jail-events uv run python src/jail-events/main.py --mode full --step clean

export-only:
	docker-compose run --rm jail-events uv run python src/jail-events/main.py --mode full --step export
