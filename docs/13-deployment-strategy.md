# LoopJob — Deployment Strategy

**Version:** 1.0 · **Status:** Draft, pending approval

---

## 1. Environments

| Env | Where | Purpose |
|-----|-------|---------|
| **dev** | Local Docker Compose | Everything, one command (`make dev`), hot reload |
| **prod** | **Railway** (primary target) | Always-on personal deployment |
| (alt) | Render / AWS (ECS or a single EC2+Compose) | Documented escape hatches; no code changes required (12-factor) |

## 2. Topology (prod)

| Service | Image | Size guidance | Notes |
|---------|-------|---------------|-------|
| `frontend` | Next.js standalone (multi-stage, distroless-ish node) | 256–512 MB | Serves dashboard; talks to API over private network |
| `api` | Python slim + uvicorn | 512 MB | FastAPI; no Playwright here |
| `worker` | Python + Playwright base image (`mcr.microsoft.com/playwright/python`) | 1–2 GB | Celery; the only heavy container; `max_tasks_per_child` recycling |
| `scheduler` | Same code image as api (different entrypoint) | 256 MB | APScheduler → enqueues to Redis |
| `postgres` | Railway managed Postgres 16 | hobby tier | pgvector enabled (fallback path documented if unavailable) |
| `redis` | Railway managed Redis | hobby tier | broker + cache + locks; persistence on (AOF) so queued tasks survive restarts |

All services: restart-on-failure policy, healthcheck endpoints/commands, resource limits.

## 3. Configuration & secrets

- Single `.env.example` documents every variable; typed/validated at boot by pydantic-settings (fail-fast on missing).
- **Env-only secrets:** `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY` (optional), `RESEND_API_KEY`, `SEARCH_API_KEY` (optional), `DASHBOARD_BASIC_AUTH` (user:hash).
- **DB-stored config:** everything user-tunable (threshold, schedule, recipient…) — editable in UI, no redeploys.
- Railway env groups per service; secrets never in images or logs (logger redaction filter).

## 4. Access & security

- Dashboard + API exposed via Railway domain behind **reverse-proxy basic auth** (Caddy sidecar or Next middleware checking `DASHBOARD_BASIC_AUTH`) — single-user product, defense in depth anyway.
- API CORS locked to the frontend origin; internal services on private network only; Postgres/Redis not publicly exposed.
- Email deliverability: Resend domain verification (SPF + DKIM) documented as a setup step; falls back to `onboarding@resend.dev` sender for first-run.

## 5. Release process

1. `main` is always deployable; feature branches → PR → CI green (lint/type/test/e2e) → squash merge.
2. Railway auto-deploys `main` per service (build from Dockerfiles). Migrations run as a **pre-deploy release command** (`alembic upgrade head`) — additive-first migration policy so old code tolerates the new schema during the deploy window.
3. Rollback = redeploy previous image (Railway one-click); DB migrations are forward-only, hence additive-first rule.
4. Post-deploy check (scripted): `/health/deep` green, scheduler next-run visible, test email sends.

## 6. Operations & monitoring

| Concern | Mechanism |
|---------|-----------|
| Liveness | `/health` per service + platform healthchecks + restart policies |
| The product heartbeat | `scan_runs` table = source of truth; Home page shows last/next scan; **external ping**: scheduler hits a healthchecks.io URL after each successful run → email alert if a scheduled scan is missed (mitigates R6 silent death) |
| Logs | Structured JSON to stdout → Railway log drain; correlation ID per scan run |
| Errors | Sentry (free tier) on api + worker + frontend |
| Cost watch | OpenAI usage is cache-bounded (~new jobs only); Railway hobby estimate ≤ $10–15/mo incl. the beefier worker |
| Backups | Railway managed Postgres daily snapshots; weekly `pg_dump` to object storage via cron task (jobs history is the irreplaceable data) |
| Data hygiene | Nightly task prunes raw crawl payloads > 30 days (retention setting) |

## 7. Runbook (committed as `docs/runbook.md` at M10)

- **A scheduled scan didn't run** → check scheduler logs → check Redis health → restart scheduler service → verify next-run repopulates.
- **Company failing** → dashboard → Verify URL → inspect crawl_result errors → fix URL / pin strategy / pause.
- **No emails arriving** → email_log status → Resend dashboard → test-email endpoint → check spam/SPF.
- **Worker OOM** → check Playwright page count → lower `scan_concurrency` → raise worker memory.
- **Rotate a key** → update Railway env → redeploy service (boot-time validation confirms).
- **Restore DB** → Railway snapshot restore; app is stateless otherwise.

## 8. Local development

```
make dev        # compose up: pg, redis, api (reload), worker, scheduler, frontend (next dev)
make seed       # 14 companies, default keywords, 8/14/20 schedule
make scan       # trigger a manual scan via API
make test       # full backend+frontend suite
make canary     # live-scrape 2 whitelisted companies (never in CI)
```
Playwright browsers installed in the worker image only; local Python venv works API-side without them. `.env` from `.env.example`; system fully functional with **zero** paid keys (local embedder, email printed to console via `ConsoleNotifier` when `RESEND_API_KEY` unset).
