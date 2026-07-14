.PHONY: dev dev-api dev-frontend install test lint typecheck migrate seed

# ── Full stack (Docker) ─────────────────────────────────────────────
dev:
	docker compose up --build

# ── No-Docker local dev (SQLite) ────────────────────────────────────
install:
	python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements-dev.txt
	cd frontend && npm install

dev-api:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# ── Quality ─────────────────────────────────────────────────────────
test:
	cd backend && .venv/bin/pytest

lint:
	cd backend && .venv/bin/ruff check app tests

typecheck:
	cd backend && .venv/bin/mypy

# ── Data (M1) ───────────────────────────────────────────────────────
migrate:
	cd backend && .venv/bin/alembic upgrade head

seed:
	cd backend && .venv/bin/python -m app.db.seed
