.PHONY: setup \
	frontend-dev frontend-build frontend-lint \
	backend-run backend-test backend-lint \
	docker-start docker-stop docker-rebuild \
	assets-process assets-manifest

## One-shot local dev bootstrap (backend venv, frontend node_modules, .env files)
setup:
	./scripts/setup.sh

## --- Frontend -------------------------------------------------------------

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-lint:
	cd frontend && npm run lint

## --- Backend --------------------------------------------------------------

backend-run:
	cd backend && uvicorn app.main:app --reload

backend-test:
	cd backend && pytest -v

backend-lint:
	cd backend && ruff check .

## --- Docker (full stack: frontend + backend + postgres + redis) -----------

docker-start:
	docker compose up --build -d

docker-stop:
	docker compose down

docker-rebuild:
	docker compose build --no-cache && docker compose up -d

## --- Z-Anatomy asset pipeline ----------------------------------------------

## Process assets/raw/Z-Anatomy/ into frontend/public/models/ (one command)
assets-process:
	python scripts/process_models.py

## Regenerate frontend/public/models/manifest.json from disk state only
assets-manifest:
	python scripts/generate_manifest.py
