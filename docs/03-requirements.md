# LoopJob — Functional & Non-Functional Requirements

**Version:** 1.0 · **Status:** Draft, pending approval

Requirement IDs: `FR-x.y` functional, `NFR-x` non-functional. **MUST** = v1 blocker, **SHOULD** = v1 target, **MAY** = future.

---

## Part A — Functional requirements

### FR-1 Company management

- **FR-1.1 (MUST)** CRUD companies: name, careers URL, optional notes.
- **FR-1.2 (MUST)** Pause/resume monitoring per company; paused companies are excluded from scheduled scans.
- **FR-1.3 (MUST)** Soft-delete companies; historical jobs retained.
- **FR-1.4 (MUST)** On-demand career-URL verification: fetch the URL, classify outcome (OK + jobs detected / OK but no jobs parsed / redirect / blocked (403/429) / not found / timeout).
- **FR-1.5 (MUST)** Track per company: last crawl attempt, last successful crawl, last strategy used, consecutive-failure count, computed health (healthy = last crawl OK; degraded = 1–2 consecutive failures; failing = ≥ 3).
- **FR-1.6 (SHOULD)** Careers-URL discovery when only a name is provided (search-engine lookup + heuristics).

### FR-2 Keyword & filter management

- **FR-2.1 (MUST)** Three keyword classes, independently manageable:
  - **Include** (role intent): Software Engineer, SDE, Backend, Platform, Infrastructure, AI Engineer, Machine Learning, University, Student, Intern, Graduate, New Grad…
  - **Requirement** (eligibility/location): 2027, Batch 2027, Expected Graduation 2027, Final Year, India, Remote, Bangalore, Hyderabad, Pune…
  - **Exclude** (hard blocks): Senior, Principal, Manager, Staff, Experienced, 5+ Years…
- **FR-2.2 (MUST)** Keyword changes take effect on the next scan without restart.
- **FR-2.3 (MUST)** Seed defaults loadable on first run (the lists above).

### FR-3 Scraping engine

- **FR-3.1 (MUST)** Strategy chain executed per company in priority order, first success wins:
  1. **Official careers page** (static fetch → parse)
  2. **Official/embedded job API** (JSON endpoints discovered from page network calls or known patterns)
  3. **Search engine** (`site:` queries against the careers domain)
  4. **Fallback search** (general web query: `"<company>" software engineer intern 2027`)
  5. **LLM extraction** (feed fetched HTML/text to an LLM to extract structured jobs)
- **FR-3.2 (MUST)** Supported source formats: static HTML, JS-rendered pages (Playwright), paginated lists, infinite scroll (bounded), JSON APIs, sitemaps, RSS/Atom, embedded structured data (JSON-LD `JobPosting`).
- **FR-3.3 (MUST)** Per-domain politeness: configurable request throttle (default ≥ 2 s between requests to one domain), rotating realistic user agents, robots.txt consulted (crawl only where appropriate; log when overridden).
- **FR-3.4 (MUST)** Retry transient failures (timeouts, 429, 5xx) with exponential backoff + jitter, max N attempts (default 3). 403/429 responses trigger UA rotation and extended backoff before the strategy is marked failed.
- **FR-3.5 (MUST)** Each crawl records: strategy used, HTTP outcomes, jobs extracted, duration, errors — persisted for the History page.
- **FR-3.6 (MUST)** Normalize extracted jobs to a canonical shape: external ID (if any), title, location(s), posting date (if available), apply URL, raw description/snippet.
- **FR-3.7 (SHOULD)** Cache raw fetch results (Redis, short TTL) so retries within a scan don't refetch.

### FR-4 Matching engine

- **FR-4.1 (MUST)** Pipeline order: **hard exclusions → semantic scoring → requirement boost → threshold**.
- **FR-4.2 (MUST)** Hard exclusions are literal/fuzzy checks on title (Senior, Principal, Staff, Manager, "N+ years"); an excluded job is stored with `excluded` status and never emailed.
- **FR-4.3 (MUST)** Semantic scoring: embed job title (+ location + snippet) and each include keyword; score = max cosine similarity across include keywords. Provider: OpenAI `text-embedding-3-small`; automatic fallback to local `sentence-transformers/all-MiniLM-L6-v2` when no API key or API failure.
- **FR-4.4 (MUST)** Keyword embeddings cached (recomputed only when a keyword changes); job embeddings cached by content hash.
- **FR-4.5 (MUST)** Requirement matching: requirement keywords matched (literal + fuzzy) against title/location/description; hits recorded and boost the final score.
- **FR-4.6 (MUST)** Configurable match threshold (default 0.55 cosine + boosts); jobs scored ≥ threshold get `matched` status.
- **FR-4.7 (MUST)** Match reasons persisted per job: list of matched include keywords (with similarity), matched requirements, e.g. `["Internship (0.91)", "Software Engineer (0.87)", "Batch 2027", "Bangalore"]`.
- **FR-4.8 (MAY)** Optional LLM adjudication pass for borderline scores (threshold ± 0.05).

### FR-5 Deduplication

- **FR-5.1 (MUST)** Job identity hash = SHA-256 of normalized `(company_id | lowercased title | normalized location | canonical apply-URL path)`. Unique index in DB.
- **FR-5.2 (MUST)** Re-crawled known jobs update `last_seen_at` only — no new row, no email.
- **FR-5.3 (MUST)** `email_sent_at` set exactly once per job; the email pipeline selects only `matched AND email_sent_at IS NULL`.

### FR-6 Scheduler

- **FR-6.1 (MUST)** User-configurable scan times (multiple per day), stored in DB, timezone-aware (default Asia/Kolkata). APScheduler with cron triggers; jobs dispatched to Celery workers.
- **FR-6.2 (MUST)** Schedule edits apply without process restart.
- **FR-6.3 (MUST)** Manual "Scan now" (global + per-company) enqueues immediately.
- **FR-6.4 (MUST)** Every scan run persisted: trigger (scheduled/manual), start/end, per-company outcomes, totals.
- **FR-6.5 (SHOULD)** Concurrency guard: a company is never scanned by two workers simultaneously (Redis lock).

### FR-7 Email notifications

- **FR-7.1 (MUST)** After each scan run, if new matched jobs exist, send exactly one digest email via Resend.
- **FR-7.2 (MUST)** Digest content per job: Company, Title, Location, Posted date, direct Apply link, match reasons ("Matched because: • Internship • Software Engineer • Batch 2027").
- **FR-7.3 (MUST)** Responsive HTML template + plaintext fallback; grouped by company; subject like `LoopJob: 4 new internship matches (Google, Nvidia +1)`.
- **FR-7.4 (MUST)** Send failures retried (3×, backoff); permanent failure logged and flagged on dashboard; `email_sent_at` set only on confirmed acceptance.
- **FR-7.5 (MUST)** Email settings (recipient, enable/disable) editable in dashboard; Resend API key env-only.
- **FR-7.6 (MAY)** Notification layer as interface (`Notifier`) with future Telegram/Discord/Slack/push implementations.

### FR-8 Dashboard

- **FR-8.1 (MUST)** Pages: Home, Companies, Keywords, Scheduler, Email Settings, Jobs Found, History, Settings, Statistics.
- **FR-8.2 (MUST)** Home cards: companies monitored, jobs found today, jobs emailed (today/total), last scan time+status, next scan time. Plus recent-matches list and unhealthy-company warnings.
- **FR-8.3 (MUST)** Jobs page: server-side search (title), filters (company, date range, matched keyword, location, status), pagination; actions: open Apply link, Mark Applied, Bookmark.
- **FR-8.4 (MUST)** History page: scan-run log with per-company drill-down (strategy, duration, jobs found, errors).
- **FR-8.5 (SHOULD)** Statistics: jobs/matches over time, per-company yield, crawl success rate, emails sent — with time-range selector.
- **FR-8.6 (MUST)** All mutating UI actions give optimistic/loading feedback and surface API errors as toasts.

---

## Part B — Non-functional requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-1 | **Reliability** | ≥ 99% of scheduled scans execute; one company's failure never aborts the scan run (isolation per company task); process crash-safe (Celery acks-late, idempotent tasks). |
| NFR-2 | **Correctness** | Zero duplicate emails (enforced at DB level via unique hash + `email_sent_at`); idempotent scan pipeline — re-running a scan produces no new side effects for already-seen jobs. |
| NFR-3 | **Performance** | Full 14-company scan ≤ 10 min wall time (companies scanned concurrently, default 4 parallel); dashboard API p95 < 300 ms; jobs list paginated (≤ 50/page). |
| NFR-4 | **Scalability (headroom)** | Design supports 100+ companies and 100k+ job rows without schema change; workers horizontally scalable. |
| NFR-5 | **Politeness / compliance** | Per-domain throttling; robots.txt respected where appropriate; identifiable but rotating UA pool; no login-walled scraping; personal-scale volumes only. |
| NFR-6 | **Security** | All secrets via environment variables (never in DB/repo); dashboard deployable behind basic auth/private network; CORS locked to the frontend origin; parameterized queries only (SQLAlchemy); dependency pinning. |
| NFR-7 | **Observability** | Structured JSON logging (loguru/structlog) with per-scan correlation IDs; every crawl/match/email decision traceable; log levels configurable. |
| NFR-8 | **Type safety** | Python: full type hints, mypy-clean; Pydantic models at all boundaries. TypeScript: strict mode; API types generated/shared. |
| NFR-9 | **Testability** | Unit tests for matching, dedup, normalization; integration tests for scraping strategies against fixture HTML; e2e smoke for API. Coverage target ≥ 80% on services/repositories. |
| NFR-10 | **Configurability** | 12-factor: all tunables (thresholds, throttles, retries, concurrency, model names) via typed settings (pydantic-settings) with sane defaults. |
| NFR-11 | **Cost** | Embedding calls minimized via caching; local embedding fallback keeps the system functional at $0; fits Railway/Render hobby tiers (≤ 1 GB RAM per service; Playwright worker may need more). |
| NFR-12 | **Maintainability** | Feature-first modular monolith; strategies/notifiers/embedders behind interfaces; adding an ATS adapter or notification channel touches only its module. |
| NFR-13 | **Portability** | Docker Compose for local + prod; deployable to Railway, Render, or AWS without code changes. |
| NFR-14 | **Data retention** | Jobs and scan history retained indefinitely by default; configurable pruning of raw crawl payloads (default 30 days). |
