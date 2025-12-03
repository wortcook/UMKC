.PHONY: help build up down restart logs clean test shell validate

# Default target
help:
	@echo "OpenGenome2 - Docker Compose Management"
	@echo ""
	@echo "Usage:"
	@echo "  make build          Build all Docker images"
	@echo "  make up             Start all services"
	@echo "  make down           Stop all services"
	@echo "  make restart        Restart all services"
	@echo "  make logs           View logs from all services"
	@echo "  make logs-follow    Follow logs in real-time"
	@echo "  make clean          Remove containers, volumes, and cache"
	@echo "  make shell          Open shell in master container"
	@echo "  make validate       Validate environment and Spark connectivity"
	@echo "  make test           Run test suite"
	@echo "  make ps             Show running containers"
	@echo "  make spark-ui       Open Spark Master UI in browser"

# Build all containers
build:
	@echo "Building Docker images..."
	docker-compose build

# Build without cache (force rebuild)
rebuild:
	@echo "Rebuilding Docker images without cache..."
	docker-compose build --no-cache

# Start all services
up:
	@echo "Starting services..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Services started. Spark Master UI: http://localhost:8081"

# Stop all services
down:
	@echo "Stopping services..."
	docker-compose down

# Restart all services
restart: down up

# View logs
logs:
	docker-compose logs

# Follow logs in real-time
logs-follow:
	docker-compose logs -f

# View logs for specific service
logs-master:
	docker-compose logs -f spark-master

logs-worker:
	docker-compose logs -f spark-worker-1 spark-worker-2

# Clean up everything
clean:
	@echo "Cleaning up containers, volumes, and cache..."
	docker-compose down -v
	rm -rf cache/* logs/*
	@echo "Cleanup complete."

# Deep clean (including data - use with caution!)
clean-all: clean
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -rf data/raw/* data/parquet/* results/*; \
		echo "All data deleted."; \
	fi

# Open shell in master container
shell:
	docker exec -it opengenome-spark-master /bin/bash

# Open Python REPL in master container
python:
	docker exec -it opengenome-spark-master python3

# Show running containers
ps:
	docker-compose ps

# Show container resource usage
stats:
	docker stats

# Validate environment
validate:
	@echo "Validating environment..."
	@docker exec opengenome-spark-master python3 --version
	@echo ""
	@echo "Checking Spark connectivity..."
	@docker exec opengenome-spark-master bash -c "curl -s http://localhost:8080 | grep -o 'Spark Master' || echo 'Spark Master not responding'"
	@echo ""
	@echo "Checking workers..."
	@docker-compose ps | grep worker

# Run tests
test:
	@echo "Running tests..."
	docker exec opengenome-spark-master pytest /opt/opengenome/tests/ -v

# Run tests with coverage
test-coverage:
	docker exec opengenome-spark-master pytest /opt/opengenome/tests/ -v --cov=/opt/opengenome/src --cov-report=html

# Scale workers
scale:
	@read -p "Number of workers: " workers; \
	docker-compose up -d --scale spark-worker=$$workers

# Open Spark Master UI
spark-ui:
	@echo "Opening Spark Master UI..."
	@open http://localhost:8081 || xdg-open http://localhost:8081 || echo "Please open http://localhost:8081 in your browser"

# Check disk usage
disk-usage:
	@echo "Disk usage for data directories:"
	@du -sh data/* results/* cache/* logs/* 2>/dev/null || echo "No data yet"
