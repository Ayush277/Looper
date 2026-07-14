# LoopJob — Testing Strategy

**Version:** 1.0 · **Status:** Draft, pending approval
**Stack:** pytest + pytest-asyncio + httpx TestClient + testcontainers (backend) · Vitest + Testing Library + Playwright Test (frontend) · GitHub Actions CI

---

## 1. Testing philosophy

- **The network is the enemy of determinism.** No live portal/OpenAI/Resend calls in CI — ever. All external I/O goes through interfaces (Fetcher, Embedder, Notifier) that are trivially fakeable, plus recorded fixtures for realism.
- **Test the decisions, not the plumbing.** The highest-value tests are: hash identity, exclusion rules, semantic-match golden set, dedup/idempotency, digest selection. These encode the product's promises (zero duplicates, no senior roles, variants matched).
- **Coverage targets:** services/repositories/matching/normalization ≥ 80%; scraping extractors ≥ 70% (fixture-driven); routers via integration tests.

## 2. Test pyramid

| Layer | Scope | Tooling | Runs |
|-------|-------|---------|------|
| **Unit** (many, ms) | Pure logic: normalizer, hashing, exclusion rules, requirement matcher, boost/threshold math, digest grouping, URL canonicalization | pytest, no I/O | every commit |
| **Integration** (dozens, s) | Repos against real Postgres (testcontainers); extractors/strategies against saved fixtures; API routes with TestClient + test DB; Celery tasks eager-mode | pytest + testcontainers | every commit |
| **E2E smoke** (few, min) | Compose stack up → seed → trigger scan (FakeFetcher serving fixtures) → job in API → mark applied → digest captured by fake notifier | pytest against composed stack; Playwright Test for UI path | PR + nightly |
| **Live canary** (manual/scheduled, not CI) | Real scan of 2–3 whitelisted companies to detect portal drift | `make canary` locally / weekly scheduled job in prod | weekly |

## 3. What gets tested, concretely

### 3.1 Normalization & dedup (the zero-duplicate promise)
- Hash stability: same job with reordered query params, trailing slashes, case/whitespace differences → same hash.
- Hash sensitivity: different location or title → different hash.
- `ON CONFLICT` path: inserting a seen job updates `last_seen_at`, returns not-new, never re-emails.
- **Property-based** (hypothesis): normalize() idempotent; hash deterministic across processes.

### 3.2 Matching (the semantic promise)
- **Golden set** (~60 labeled pairs, committed as YAML):
  - must-match: "Software Development Engineer Intern" ↔ "Software Engineer Internship"; "University Hiring" ↔ keywords {Campus Hiring, Graduate Program, Internship, New Grad}; "SDE-1 (New Grad)" ↔ "New Grad"…
  - must-exclude: "Senior Software Engineer", "Staff ML Engineer", "Engineering Manager", "SDE III (7+ years)"…
  - must-not-match: "Sales Intern", "Legal Counsel", "Product Marketing Manager"…
- Runs with **both** embedders: recorded OpenAI vectors (fixture JSON, so CI needs no key) and live local MiniLM. CI prints precision/recall; gate ≥ 90% agreement.
- Requirement matcher: "Bangalore" matches "Bengaluru, KA, India" (alias table); "2027" matches "Batch of 2027" / "graduating 2027".
- Exclusion regexes: "5+ Years", "7-10 years", "at least six years experience".

### 3.3 Scraping (fixture-driven)
- `tests/fixtures/portals/` — saved real responses per seed company (HTML pre/post-render, JSON API payloads, sitemaps, RSS), refreshed manually via `make record-fixtures`.
- Each extractor: fixture in → expected normalized jobs out (snapshot-tested).
- Strategy chain: FakeFetcher scripts failure sequences → assert fallback order, `strategies_attempted` audit trail, preferred-strategy memory update.
- Fetcher unit tests: backoff timing (frozen clock), UA rotation, per-domain throttle (fakeredis), robots.txt parsing, fetch cache hit/miss.

### 3.4 Orchestration & scheduler
- Idempotency: run the same scan twice over identical fixtures → second run inserts 0 rows, sends 0 emails.
- Isolation: company #3 raises → run completes `completed_with_errors`, other 13 unaffected, health updated only for #3.
- Concurrency lock: two simultaneous `scan_company` for one company → second no-ops.
- APScheduler: schedule row change → trigger set updates without restart (time-mocked).

### 3.5 Email
- Digest selection query: exactly `matched AND email_sent_at IS NULL`; excluded/unmatched/already-sent never selected.
- Transactionality: notifier failure → `email_sent_at` stays NULL (retried next run); notifier success + DB commit → set exactly once.
- Template: renders with 1 job, 20 jobs, missing posted_at/location; HTML passes premailer inline check; plaintext non-empty. Manual matrix (Gmail web/mobile, Apple Mail) at M5.

### 3.6 API & frontend
- API: per-route happy path + validation errors + 404/409 cases; pagination/filter combinations on `/jobs`; error envelope shape.
- Frontend: Vitest component tests for StatCard/JobRow/ReasonChip logic; TanStack Query hooks with mocked client; one Playwright path per page (P0 flows), run against the composed stack with fixtures.
- Contract: generated TS client from OpenAPI must compile — drift fails CI.

## 4. Failure-mode drills (M9, scripted, repeatable)

| Drill | Expected behavior |
|-------|-------------------|
| Redis down mid-scan | Scan fails loudly, scan_run=failed, API stays up, next scheduled scan recovers |
| Postgres down | API 503 with envelope; worker retries then parks; no partial digest |
| OpenAI 500s | Automatic local-embedder fallback, logged, scan completes |
| Resend 500s | 3 retries → email_log failed → dashboard flag; jobs remain queued for next run |
| Worker killed mid-run (SIGKILL) | acks-late redelivery; idempotency prevents duplicates |
| Portal returns CAPTCHA page | Extraction empty → fallback chain proceeds → health degraded, no crash |

## 5. CI pipeline (GitHub Actions)

```
lint (ruff, eslint, prettier)  →  typecheck (mypy, tsc)  →  unit  →
integration (testcontainers: pg+redis)  →  build images  →  e2e smoke  →
golden-set report (comment on PR)
```
- PRs blocked on all stages; nightly job additionally runs e2e + golden set with live local embedder.
- Weekly prod canary (2 real portals) alerts on extraction drift — the early-warning system for R1.
