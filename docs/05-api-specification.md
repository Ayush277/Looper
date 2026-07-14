# LoopJob — API Specification

**Version:** 1.0 · **Status:** Draft, pending approval
**Style:** REST/JSON · **Base URL:** `/api/v1` · **Framework:** FastAPI (OpenAPI auto-generated at `/docs`)
**Auth (v1):** none at app level (single user); deployment sits behind private network or reverse-proxy basic auth. All handlers structured so a bearer-token dependency can be added later without route changes.

---

## 1. Conventions

- **IDs:** UUID strings.
- **Timestamps:** ISO 8601 with offset (`2026-07-14T08:00:00+05:30`).
- **Pagination:** `?page=1&page_size=25` (max 50) → response envelope `{ "items": [...], "total": 132, "page": 1, "page_size": 25 }`.
- **Errors:** RFC-7807-ish body:
  ```json
  { "error": { "code": "company_not_found", "message": "Company 3f2a… does not exist", "details": {} } }
  ```
  Status codes: 400 validation, 404 missing, 409 conflict (duplicates), 422 semantic validation, 500 unexpected, 503 dependency down.
- **Validation:** Pydantic v2 request/response models; the OpenAPI schema is the contract for frontend type generation (`openapi-typescript`).

## 2. Endpoints

### 2.1 Companies

| Method | Path | Description |
|--------|------|-------------|
| GET | `/companies` | List companies. Query: `status` (active/paused/all), `health`, `search`, pagination. |
| POST | `/companies` | Create. Body: `{ "name": "Google", "careers_url": "https://careers.google.com/jobs" }` (`careers_url` optional → triggers async discovery). 409 on duplicate name. |
| GET | `/companies/{id}` | Detail incl. health, last crawls, recent `crawl_results` (last 10), job counts. |
| PATCH | `/companies/{id}` | Update `name`, `careers_url`, `notes`. Changing `careers_url` resets `careers_url_verified_at` and health. |
| DELETE | `/companies/{id}` | Soft delete (`status='deleted'`). |
| POST | `/companies/{id}/pause` | `status='paused'`. |
| POST | `/companies/{id}/resume` | `status='active'`. |
| POST | `/companies/{id}/verify` | Live URL verification (async task). → `202 { "task_id": "..." }`; result polled via `/tasks/{task_id}`. |
| POST | `/companies/{id}/scan` | Manual scan of one company. → `202 { "scan_run_id": "..." }`. |

**Company resource:**
```json
{
  "id": "…", "name": "Google",
  "careers_url": "https://careers.google.com/jobs",
  "careers_url_verified_at": "2026-07-14T08:01:22+05:30",
  "status": "active", "health": "healthy",
  "consecutive_failures": 0, "preferred_strategy": "job_api",
  "last_crawl_at": "…", "last_success_at": "…",
  "jobs_total": 42, "jobs_matched": 7,
  "notes": null, "created_at": "…", "updated_at": "…"
}
```

### 2.2 Keywords

| Method | Path | Description |
|--------|------|-------------|
| GET | `/keywords` | List. Query: `kind` (include/requirement/exclude). |
| POST | `/keywords` | Create `{ "term": "Backend", "kind": "include" }`. 409 on duplicate (term, kind). Include-kind triggers async embedding computation. |
| PATCH | `/keywords/{id}` | Update `term` (re-embeds) or `enabled`. |
| DELETE | `/keywords/{id}` | Hard delete (match history keeps its own JSON snapshot in `jobs.match_reasons`). |

### 2.3 Jobs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/jobs` | List with server-side filtering. Query: `search` (title ILIKE), `company_id`, `status` (matched/excluded/unmatched/all; default matched), `user_state` (bookmarked/applied), `location`, `keyword` (matched term), `posted_after`, `posted_before`, `first_seen_after`, `sort` (first_seen/-first_seen/posted_at/score), pagination. |
| GET | `/jobs/{id}` | Full detail incl. match reasons, email log refs. |
| POST | `/jobs/{id}/state` | `{ "user_state": "applied" \| "bookmarked" \| "none" }`. |

**Job resource (list item):**
```json
{
  "id": "…", "company": { "id": "…", "name": "Nvidia" },
  "title": "Software Engineering Intern — 2027",
  "location": "Bangalore, India",
  "apply_url": "https://nvidia.wd5.myworkdayjobs.com/…",
  "posted_at": "2026-07-13",
  "first_seen_at": "2026-07-14T08:03:11+05:30",
  "status": "matched", "match_score": 0.89,
  "match_reasons": [
    { "term": "Internship", "kind": "include", "similarity": 0.91 },
    { "term": "Software Engineer", "kind": "include", "similarity": 0.87 },
    { "term": "Batch 2027", "kind": "requirement" },
    { "term": "Bangalore", "kind": "requirement" }
  ],
  "email_sent_at": "2026-07-14T08:05:02+05:30",
  "user_state": "none", "source_strategy": "job_api"
}
```

### 2.4 Scans & history

| Method | Path | Description |
|--------|------|-------------|
| POST | `/scans` | Trigger global manual scan. → `202 { "scan_run_id": "..." }`. 409 if a run is already in progress. |
| GET | `/scans` | Paginated run history (newest first). |
| GET | `/scans/{id}` | Run detail + all `crawl_results` (per-company strategy, status, counts, errors). |
| GET | `/scans/current` | The in-progress run (or 404) — used for live progress UI. |

### 2.5 Scheduler

| Method | Path | Description |
|--------|------|-------------|
| GET | `/schedules` | List slots + computed `next_run_at`. |
| POST | `/schedules` | `{ "hour": 8, "minute": 0 }`. 409 duplicate. Applies live to APScheduler. |
| PATCH | `/schedules/{id}` | Edit time / `enabled`. |
| DELETE | `/schedules/{id}` | Remove slot. |

### 2.6 Settings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/settings` | Full settings row (timezone, notification_email, email_enabled, match_threshold, requirement_boost, scan_concurrency, embedding_provider) + read-only computed flags (`openai_key_present`, `resend_key_present`). |
| PATCH | `/settings` | Partial update of the above (never secrets). |
| POST | `/settings/test-email` | Send a test digest to `notification_email`. → 202. |

### 2.7 Stats & dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/stats/overview` | Home-page cards: `{ "companies_active": 14, "companies_failing": 1, "jobs_found_today": 9, "jobs_matched_today": 4, "emails_sent_today": 1, "jobs_emailed_total": 63, "last_scan": { "at": "…", "status": "completed" }, "next_scan_at": "…" }` |
| GET | `/stats/timeseries` | Query: `metric` (jobs_found/jobs_matched/emails_sent/crawl_success_rate), `range` (7d/30d/90d), `bucket` (day). → `[{ "date": "2026-07-14", "value": 4 }]` |
| GET | `/stats/companies` | Per-company yield table (jobs found/matched, success rate, last success). |

### 2.8 Async task status

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks/{task_id}` | Generic Celery task poll: `{ "status": "pending" \| "running" \| "success" \| "failure", "result": {...} }`. Used by verify-URL and test-email UIs. |

### 2.9 Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness: `{ "status": "ok" }`. |
| GET | `/health/deep` | Checks DB, Redis, Celery ping, embedding provider reachability: per-dependency status. |

## 3. Realtime updates

v1 uses **polling** (dashboard refetches `/scans/current` every 3 s while a scan runs; SWR-style revalidation elsewhere). SSE/WebSocket is deliberately deferred — polling is sufficient at single-user scale and removes a failure mode.

## 4. Versioning & compatibility

- Path-versioned (`/api/v1`). Additive changes (new fields) are non-breaking; removals/renames require `/api/v2`.
- Frontend TypeScript types are generated from the OpenAPI schema in CI — drift fails the build.
