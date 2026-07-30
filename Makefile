# Convenience commands for local development.
# Usage: `make <target>`

.PHONY: help up down logs build backend-dev frontend-dev backend-install frontend-install test

help:
	@echo "Available targets:"
	@echo "  up               Start the full stack via Docker Compose"
	@echo "  down             Stop and remove containers"
	@echo "  logs             Tail logs from all services"
	@echo "  build            Rebuild all images"
	@echo "  backend-install  Install backend dependencies locally"
	@echo "  backend-dev      Run the backend with autoreload (local)"
	@echo "  frontend-install Install frontend dependencies locally"
	@echo "  frontend-dev     Run the frontend dev server (local)"
	@echo "  test             Run backend tests"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

backend-install:
	cd backend && pip install -r requirements.txt -r requirements-dev.txt

backend-dev:
	cd backend && PYTHONPATH=.. uvicorn app.main:app --reload --reload-exclude "../data/*" --host 0.0.0.0 --port 8000

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

test:
	cd backend && PYTHONPATH=.. pytest -q
