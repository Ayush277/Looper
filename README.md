# LoopJob

**Never miss another internship opening.**

A personal, always-on agent that monitors company career portals, discovers matching jobs across the indexed job market (keyword + country), semantically matches them against your filters, and emails you new openings — deduplicated, with the reason each one matched.

## Documentation

Docs-first project — full PRD, architecture, and roadmap in [docs/](docs/00-INDEX.md). Implementation progress: [PROGRESS.md](PROGRESS.md).

## Quick start (local, no Docker)

```bash
make install        # backend venv + frontend npm install
cp .env.example .env
make dev-api        # FastAPI on :8000 (SQLite dev DB) — /docs for swagger
make dev-frontend   # Next.js on :3000
```

## Full stack (Docker)

```bash
make dev            # postgres + redis + api + frontend
```

## Stack

Next.js · TypeScript · Tailwind · shadcn/ui — FastAPI · SQLAlchemy · Celery · APScheduler — PostgreSQL · Redis — Playwright · httpx · BeautifulSoup — OpenAI embeddings (local sentence-transformers fallback) — Resend
