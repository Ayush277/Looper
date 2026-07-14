# LoopJob — Implementation Progress

Live checklist, per [docs/10-development-roadmap.md](docs/10-development-roadmap.md). One feature at a time; a milestone is checked only when its exit criteria pass.

## M0 — Scaffolding & infrastructure
- [x] Monorepo layout (backend / frontend / docs)
- [x] Backend: FastAPI skeleton, typed settings (pydantic-settings), structured logging (loguru)
- [x] `/api/v1/health` + `/api/v1/health/deep` (verified live)
- [x] SQLite dev fallback (no Docker required locally); Postgres+pgvector in compose for prod parity
- [x] `docker-compose.yml` (postgres, redis, api, frontend; worker/scheduler arrive with M4)
- [x] Makefile (`dev`, `dev-api`, `dev-frontend`, `test`, `lint`, `typecheck`, `migrate`, `seed`)
- [x] `.env.example` documenting every variable
- [x] Lint/type tooling: ruff, mypy (strict), pytest configured
- [x] Frontend: Next.js 16 + TypeScript + Tailwind v4 scaffold (`next build` green, 10 routes)
- [x] Frontend: app shell (sidebar nav, dark theme per design system) — verified in browser
- [ ] CI (GitHub Actions: lint, typecheck, test) — needs GitHub remote
- ⚠ Docker not installed on this machine — compose stack untested locally; `make dev-api`/`dev-frontend` is the local path

## M1 — Data layer & seed
- [x] SQLAlchemy models — all 10 tables (docs/04 + discovery_queries/origin from docs/15), SQLite/Postgres portable
- [x] Alembic async setup + `initial schema` migration (applied & verified: 11 tables)
- [x] Hash / normalization utilities + 9 unit tests (dedup identity rules proven)
- [x] Seed script, idempotent (14 companies, 27 keywords, 8/14/20 schedule, settings, 1 discovery query)
- [x] Quality gates: ruff clean, mypy --strict clean, pytest green
- [ ] Repositories — built per-feature as each feature milestone lands (feature-first structure)

## M2 — Scraping engine (in progress)
- [x] Fetcher: per-domain throttle, UA rotation, exponential backoff + jitter, robots.txt, transient-status retries
- [x] Extractors: JSON-LD JobPosting (incl. @graph), HTML heuristic (dense-cluster detection), ATS probers (Greenhouse / Lever / Ashby with slug guessing)
- [x] Strategy chain with per-company preferred-strategy memory + full attempt audit trail
- [x] CLI: `python -m app.scraping.cli scan-company <name> [--url] [--save]` / `scan-all`
- [x] Save path: hash dedup insert, company health + last_crawl/last_success updates
- [x] 10 new tests (extractors + chain fallback/preferred/crash isolation) — 19 total, all green; ruff + mypy --strict clean
- [x] **Live proof:** Rubrik auto-discovered on Greenhouse → 97 jobs saved; rescan → 0 new (dedup + strategy memory verified)
- [x] Playwright rendering escalation (JS-shell detection + blocked-status 403/406 fallback)
- [x] Workday CxS prober (Adobe ✓ 40, Nvidia ✓ 40) · SmartRecruiters prober
- [x] Custom adapters: Amazon (✓ 197 intern/grad jobs), Microsoft (blocked by local TLS issue — retest on deploy)
- [x] Careers URLs seeded for all 14 companies
- [x] Precision hardening after live audit: job links must carry an ID (killed Amazon/Intuit/Atlassian nav-noise extraction); name-guessed ATS slugs only without own careers URL (killed LinkedIn squatter test board) — regression tests added
- [x] **Coverage: 5/14 verified-real (Amazon 197, Rubrik 97, Adobe 40, Nvidia 40, Intuit 15 = 389 jobs)**; 24 tests green
- [ ] Remaining 9: Google (robots.txt disallow — needs search-engine strategy), Microsoft (env TLS), Uber/Cisco/Salesforce/Oracle/Atlassian/Visa/LinkedIn (lazy-loading JS portals → need search strategy w/ API key, smarter render waits, or LLM extraction from M3)
- [ ] Sitemap/RSS extractors · fixture recording (`make record-fixtures`) — target ≥10/14 before M2 exit

## M3 — Matching engine (core complete)
- [x] Embedder interface: OpenAI (text-embedding-3-small via httpx) + LocalEmbedder (MiniLM, $0/offline) + automatic fallback wrapper
- [x] Hard-exclusion rules: word-boundary seniority terms + years-of-experience regex family ("5+ years", "4-6 yrs", "at least 3 years"); no substring false positives (Staffing ≠ Staff)
- [x] Requirement matcher with aliases (Bangalore↔Bengaluru, 2027↔"batch 2027"…)
- [x] MatchPipeline: exclusions → max-cosine vs include keywords → requirement boost (capped) → threshold; reasons with similarities persisted per job; embeddings cached on rows
- [x] Golden-set integration test (22 labeled titles incl. brief's canonical pairs) — ≥90% gate, passing with real MiniLM
- [x] CLI: `python -m app.matching.cli run [--all] | report`
- [x] **Live run over 389 real jobs: 39 matched / 141 excluded / 209 unmatched** — e.g. Adobe "Software Development Engineer" Bangalore 0.88 with reasons (SDE 0.83, SWE 0.79, Bangalore); Amazon "2027 Software Dev Engineer Intern" matched with 2027 hit
- [x] 33 unit + 1 integration tests green; ruff + mypy --strict clean
- [ ] Optional LLM adjudication for borderline band (FR-4.8, deferred)

## M4-lite — Scheduler & orchestration (dev mode complete)
- [x] ScanOrchestrator: full run end-to-end (scan → dedup insert → match → digest → email log), per-company isolation, crawl_results audit, health updates
- [x] In-process APScheduler reading schedules table (live reload on edit, timezone-aware) — verified next-run 08:00 IST
- [x] **Live e2e via API: scan run → 29 new jobs → matched → digest with reasons "sent" (console) → email_sent_at stamped; queue drained to 0 (zero-dup proof)**
- [ ] Full M4 (Celery workers + Redis locks + separate scheduler process) — needs Docker/Redis

## M5 — Email digests (complete in dev mode)
- [x] Notifier interface; ResendNotifier (ready, needs key) + ConsoleNotifier (active)
- [x] Responsive HTML digest template (Jinja2, email-safe tables, inline CSS) + plaintext
- [x] Transactional email_sent_at + email_logs + email_log_jobs — 41 jobs emailed exactly once
- [ ] Real Resend send + Gmail render check — needs RESEND_API_KEY

## M6 — API (core complete)
- [x] Companies CRUD + pause/resume/scan · Keywords CRUD · Jobs list w/ filters+pagination + state · Scans trigger/list/current/detail · Schedules CRUD (live scheduler reload) · Settings get/patch · Stats overview
- [x] Dev CORS for any localhost port
- [ ] /stats/timeseries, /companies/{id}/verify, discovery endpoints (M5D)

## M7 — Dashboard (core pages wired & verified in browser)
- [x] Home: live stat cards (5s refresh), Scan now button, failing-company warning
- [x] Jobs: tabs (Matched/All/Bookmarked/Applied/Excluded), search, pagination, score+reason chips, Apply/Mark applied/Bookmark
- [x] Companies: health-colored table, last success, strategy, per-company Scan/Pause/Delete, add form
- [x] Keywords: three-column board with add/delete
- [x] Scheduler: slot editor + next-run display · Email: recipient+toggle+provider status · Settings: threshold slider, boost, concurrency, key status · History: run log with per-company drill-down
- [ ] Statistics page charts (placeholder) · Discovery page (M5D)

## M8 — Statistics (complete)
- [x] API: /stats/timeseries (daily found/matched/emailed), /stats/companies (yield + health), /stats/funnel
- [x] Statistics page: pipeline funnel, per-company bars with health dots, 14-day chart — verified in browser
- [x] Discovery page: activation guide + seeded query display (full board unlocks with JSEARCH key)

## Precision hardening (ongoing audits)
- [x] Category-count noise rule ("Product Development ( 475 )" ≠ job) — caught via Oracle live audit, rows purged
- [x] Renderer: networkidle wait + lazy-load scrolling (unlocked LinkedIn via careers_page)
- [x] Cisco URL corrected to /search-results (still JS-gated — needs search strategy)

## Remaining — blocked on user-side items
- [x] **Real inbox emails via Resend — verified delivered** (message id 8a511983…, 6 jobs w/ reasons)
- [~] JSearch key wired & valid (job-details endpoint verified) — but this API version 404s on every known /search route; need the exact search endpoint snippet from the RapidAPI dashboard 'Endpoints' tab to finish the search strategy + discovery
- [ ] Full M4 (Celery workers, Redis locks, separate scheduler) + Postgres parity → Docker Desktop
- [ ] M9 failure drills at full · M10 Railway deploy + 7-day soak (after the above)
