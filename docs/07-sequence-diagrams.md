# LoopJob — Sequence Diagrams

**Version:** 1.0 · **Status:** Draft, pending approval

---

## 1. Scheduled scan (the core loop)

```mermaid
sequenceDiagram
    autonumber
    participant APS as Scheduler (APScheduler)
    participant R as Redis (broker/locks)
    participant W as Celery Worker
    participant O as ScanOrchestrator
    participant P as Career Portal
    participant M as MatchPipeline
    participant DB as PostgreSQL
    participant RS as Resend

    APS->>R: enqueue run_scan(trigger="scheduled")
    R->>W: deliver run_scan
    W->>DB: INSERT scan_run(status=running)
    W->>DB: SELECT active companies
    loop per company (concurrency = 4, isolated failures)
        W->>R: acquire lock scan:{company_id}
        W->>O: scan_company(company)
        O->>O: resolve strategy chain (preferred first)
        O->>P: fetch (throttled, UA-rotated, retries)
        P-->>O: HTML / JSON
        O->>O: extract + normalize → RawJob[] + content hashes
        O->>DB: INSERT jobs ON CONFLICT(hash) DO UPDATE last_seen_at
        DB-->>O: newly inserted rows only
        O->>M: match(new jobs, keywords)
        M->>M: hard exclusions → embed → similarity → boost → threshold
        M->>DB: UPDATE jobs SET status, score, reasons
        O->>DB: INSERT crawl_result (strategy, counts, duration)
        O->>DB: UPDATE company health, last_success_at, preferred_strategy
        W->>R: release lock
    end
    W->>DB: SELECT jobs WHERE status=matched AND email_sent_at IS NULL
    alt new matches exist
        W->>RS: send digest (HTML, grouped by company, reasons)
        RS-->>W: accepted (message_id)
        W->>DB: INSERT email_log + email_log_jobs; SET email_sent_at (same txn)
    else none
        W->>W: skip email
    end
    W->>DB: UPDATE scan_run (status=completed, totals)
```

## 2. Strategy chain with fallback (one company)

```mermaid
sequenceDiagram
    autonumber
    participant O as ScanOrchestrator
    participant F as Fetcher
    participant P as Portal
    participant SE as Search Engine
    participant LLM as LLM

    O->>F: CareersPageStrategy: GET careers_url
    F->>P: httpx GET (UA #1)
    P-->>F: 200, but JS-shell HTML (no jobs parseable)
    F->>P: Playwright render
    P-->>F: rendered DOM
    alt jobs extracted
        F-->>O: RawJob[] ✓ (record strategy=careers_page)
    else extraction empty
        O->>F: JobApiStrategy: probe JSON endpoints / sitemap / RSS / JSON-LD
        P-->>F: 404 on probes
        O->>SE: SearchEngineStrategy: site:careers.x.com intern 2027
        SE-->>O: result URLs
        O->>F: fetch each result page
        alt jobs extracted
            F-->>O: RawJob[] ✓ (strategy=search_engine)
        else still nothing
            O->>LLM: LlmExtractionStrategy: raw text → structured JobPosting[]
            LLM-->>O: JSON jobs (validated by Pydantic) ✓ or final failure
        end
    end
    O->>O: record strategies_attempted + failure causes in crawl_result
    Note over O: On total failure: consecutive_failures += 1<br/>health → degraded/failing; surfaced on dashboard
```

## 3. Retry / block handling inside the Fetcher

```mermaid
sequenceDiagram
    autonumber
    participant S as Strategy
    participant F as Fetcher
    participant R as Redis (rate buckets)
    participant P as Portal

    S->>F: get(url)
    F->>R: check domain token bucket
    R-->>F: wait 2s (throttle)
    F->>P: GET (UA #1)
    P-->>F: 429 Too Many Requests
    F->>F: backoff 4s + jitter, rotate UA
    F->>P: GET (UA #2)
    P-->>F: 503
    F->>F: backoff 9s + jitter, rotate UA
    F->>P: GET (UA #3)
    alt success
        P-->>F: 200 → cache body (Redis, TTL 15m)
        F-->>S: Response
    else attempts exhausted
        F-->>S: FetchError(cause) → strategy fails → chain continues
    end
```

## 4. User adds a company & verifies URL

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant FE as Frontend
    participant API as FastAPI
    participant W as Worker
    participant P as Portal
    participant DB as PostgreSQL

    U->>FE: Add "Rubrik" + careers URL
    FE->>API: POST /companies
    API->>DB: INSERT company (status=active, health=unknown)
    API-->>FE: 201 company
    U->>FE: click "Verify URL"
    FE->>API: POST /companies/{id}/verify
    API->>W: enqueue verify_url task
    API-->>FE: 202 {task_id}
    loop poll every 2s
        FE->>API: GET /tasks/{task_id}
    end
    W->>P: fetch + attempt extraction
    P-->>W: 200 + 37 job cards parsed
    W->>DB: UPDATE careers_url_verified_at, health=healthy
    FE->>API: GET /tasks/{task_id}
    API-->>FE: success {reachable: true, jobs_detected: 37, strategy: careers_page}
    FE-->>U: ✓ "URL verified — 37 jobs detected"
```

## 5. Manual "Scan now" with live progress

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant FE as Frontend
    participant API as FastAPI
    participant W as Worker
    participant DB as PostgreSQL

    U->>FE: click "Scan now"
    FE->>API: POST /scans
    API->>DB: guard: no scan_run in status=running (else 409)
    API->>W: enqueue run_scan(trigger=manual)
    API-->>FE: 202 {scan_run_id}
    loop poll /scans/current every 3s
        FE->>API: GET /scans/current
        API->>DB: run + crawl_results so far
        API-->>FE: {companies_ok: 9/14, jobs_new: 6, …}
        FE-->>U: progress bar + per-company ticks
    end
    W->>DB: scan_run → completed
    FE->>API: GET /scans/{id}
    FE-->>U: summary toast: "6 new jobs, 3 matched, email sent"
```

## 6. Keyword change → re-embedding

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant API as FastAPI
    participant W as Worker
    participant E as Embedder (OpenAI→local)
    participant DB as PostgreSQL

    U->>API: POST /keywords {"term": "Platform Engineer", "kind": "include"}
    API->>DB: INSERT keyword (embedding NULL)
    API->>W: enqueue embed_keyword(id)
    API-->>U: 201
    W->>E: embed("Platform Engineer")
    alt OpenAI ok
        E-->>W: vector(1536), model tag
    else OpenAI down / no key
        E-->>W: local MiniLM vector(384), model tag
    end
    W->>DB: UPDATE keyword SET embedding, embedding_model
    Note over W,DB: Next scan automatically uses the new keyword.<br/>Existing jobs are NOT retro-matched in v1 (future: re-match action).
```
