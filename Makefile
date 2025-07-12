.PHONY: build dev up down test migrate clean lint

# Variables
ENV_FILE := .env
DEV_ENV_FILE := .env.dev
SERVICE_NAME := auth-service

# Main commands
build:
	docker-compose -f docker-compose.dev.yml build

dev:
	docker-compose -f docker-compose.dev.yml up --build -d


down:
	docker-compose -f docker-compose.dev.yml down

# Migration commands
migrate:
	docker-compose exec $(SERVICE_NAME) alembic upgrade head

migrations-generate:
	docker-compose exec $(SERVICE_NAME) alembic revision --autogenerate -m "$(message)"

# Run FastAPI locally (for local development)
run-local:
	uvicorn src.app:app --reload --host localhost --port 8000

# # Testing and linting
# test:
# 	docker-compose exec $(SERVICE_NAME) pytest


format:
	docker-compose exec $(SERVICE_NAME) isort src
	docker-compose exec $(SERVICE_NAME) black src

# FastAPI documentation
docs:
	@echo "API documentation available at: http://localhost:8000/docs"
	@echo "Alternative documentation: http://localhost:8000/redoc"

# Helper commands
env-setup:
	cp -n $(DEV_ENV_FILE).example $(DEV_ENV_FILE) || true
	cp -n $(ENV_FILE).example $(ENV_FILE) || true

clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

help:
	@echo "Available commands:"
	@echo "  make build        - Build Docker containers"
	@echo "  make dev          - Run service in development mode"
	@echo "  make down         - Stop service"
	@echo "  make run-local    - Run FastAPI locally with auto-reload"
	@echo "  make migrate      - Apply migrations"
	@echo "  make migrations-generate message=\"Description\" - Create new migration"
	@echo "  make docs         - Information about API documentation access"
	@echo "  make env-setup    - Create environment files from examples"
	@echo "  make clean        - Clean temporary files"