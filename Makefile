VENV       ?= backend/.venv
PYTHON     := $(VENV)/bin/python
RUFF       := $(VENV)/bin/ruff
PIP        := $(VENV)/bin/pip
NPM        := npm
E2E_DB     := /tmp/portal-e2e.db

.DEFAULT_GOAL := help

.PHONY: help setup backend-deps frontend-deps \
        test test-backend test-frontend lint format \
        latency validate seed run-backend run-frontend \
        clean

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: backend-deps frontend-deps ## Install backend + frontend dependencies (first time)
	@echo "Setup complete. Run 'make test' to verify."

backend-deps: $(VENV)/bin/python ## Install backend dependencies into $(VENV)
	$(PIP) install -e "backend[dev]"

$(VENV)/bin/python:
	python3 -m venv $(VENV)

frontend-deps: ## Install frontend dependencies
	$(NPM) install --prefix frontend

test: lint test-backend test-frontend ## Run all checks (lint + backend + frontend)

test-backend: ## Run backend pytest suite
	$(PYTHON) -m pytest backend/tests

lint: ## Ruff lint + format check on backend
	$(RUFF) check backend/src backend/tests
	$(RUFF) format --check backend/src backend/tests

format: ## Auto-fix with ruff (lint + format)
	$(RUFF) check --fix backend/src backend/tests
	$(RUFF) format backend/src backend/tests

latency: ## Latency regression gate (Art. IV: 2s pages / 5s search p95)
	$(PYTHON) -m pytest backend/tests/contract/test_latency.py

test-frontend: ## TypeScript check + Playwright suite (fresh e2e DB)
	cd frontend && npx tsc --noEmit
	rm -f $(E2E_DB)
	cd frontend && npx playwright test

validate: ## End-to-end validation: lint, tests, latency, UI
	$(MAKE) test
	$(MAKE) latency

seed: ## Seed the database from vendored source files (backend/data)
	$(PYTHON) -c "import sys; sys.path.insert(0, 'backend/src'); \
		from portal.config import load_settings; from portal.db import create_session_factory, init_db; \
		from portal.ingestion.services import IngestionService; \
		s = load_settings(); sf = create_session_factory(s.db_path); init_db(sf); \
		IngestionService(sf, data_dir=s.data_dir).seed(); print('seed complete')"

run-backend: ## Start the FastAPI backend (uvicorn, port 8000)
	$(VENV)/bin/uvicorn "portal.main:create_app" --factory --app-dir backend/src --port 8000 --reload

run-frontend: ## Start the Next.js frontend dev server (port 3000)
	$(NPM) --prefix frontend run dev

clean: ## Remove virtualenv, node_modules, and the SQLite database
	rm -rf $(VENV) frontend/node_modules backend/portal.db
