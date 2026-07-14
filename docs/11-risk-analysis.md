# LoopJob — Risk Analysis

**Version:** 1.0 · **Status:** Draft, pending approval
Scoring: Likelihood × Impact, 1–5 each. **Score ≥ 12 = red** (needs designed-in mitigation, not hope).

---

## Risk register

| ID | Risk | L | I | Score | Mitigation (designed in) | Residual plan |
|----|------|---|---|-------|--------------------------|---------------|
| R1 | **Portal structure changes break scrapers** — the certainty risk; every portal will change eventually | 5 | 4 | **20** | Strategy *chain* (5 fallbacks) so one break degrades, not blinds; per-company health + consecutive-failure tracking surfaces breaks within one scan; LLM extraction as structure-agnostic last resort; fixture tests catch regressions in our parsing | Monthly operator pass on `failing` companies; fix or re-point URL |
| R2 | **Bot detection / blocking (403, 429, Cloudflare)** — Workday/Greenhouse-hosted portals especially | 4 | 4 | **16** | Personal-scale volume (≤3 scans/day); per-domain throttle ≥2s; rotating realistic UAs; exponential backoff; Playwright with real browser fingerprint as escalation; search-engine strategy bypasses the portal entirely | If a portal hard-blocks: rely on search/LLM strategies; worst case mark company "search-only" |
| R3 | **JS-heavy portals unparseable without rendering** | 4 | 3 | **12** | Playwright escalation built into Fetcher; JSON-API probing often finds the underlying XHR endpoint (cheaper + more stable than DOM) | Per-company notes for manual endpoint pinning |
| R4 | **Semantic matcher noise** — false positives (spam) or false negatives (missed postings) | 3 | 4 | **12** | Hard exclusions guarantee precision floor; golden-set test (~60 labeled pairs) gates changes; threshold + boost user-tunable; match reasons make every decision auditable so drift is noticed | Tune threshold from Statistics funnel; add LLM adjudication for borderline band (FR-4.8) |
| R5 | **Duplicate emails** (the cardinal UX sin per brief) | 2 | 5 | 10 | DB-level unique `content_hash` + `email_sent_at` set transactionally with email_log; idempotent `ON CONFLICT` inserts; tested explicitly (M4/M5 exit criteria) | Alert if email_log shows same job twice (should be impossible) |
| R6 | **Scheduler silently dies** → no scans, no signal (silent failure = missed internships) | 3 | 5 | **15** | Scheduler is stateless + auto-restarting (Docker restart policy); scan_runs table = heartbeat; Home page shows "last scan" prominently — a stale timestamp is visible at first glance; deep-health endpoint | Optional external uptime ping (healthchecks.io) in deployment doc |
| R7 | **OpenAI API outage/cost spike** | 2 | 3 | 6 | Local sentence-transformers fallback (automatic); embedding cache means steady-state cost ≈ new-job volume only (~pennies/month) | Switch `embedding_provider=local` in settings |
| R8 | **Resend delivery failure / spam-foldering** | 2 | 4 | 8 | Retries with backoff; email_log records provider errors; plaintext part + clean HTML reduce spam scoring; test-email button for verification | Dashboard shows last-email status; SPF/DKIM setup documented |
| R9 | **Playwright resource exhaustion on small hosts** (OOM on 512MB tiers) | 3 | 3 | 9 | Playwright only as escalation; single browser instance, page pooling; worker memory limits + Celery `max_tasks_per_child` recycling; worker sized separately in deployment | Reduce scan concurrency; upgrade worker instance only |
| R10 | **Legal/ToS concerns around scraping** | 2 | 3 | 6 | Public pages only, no login walls, no CAPTCHA circumvention; robots.txt respected where appropriate; personal-scale read-only volume; polite throttling | Pause any company that objects; search-engine strategy uses only indexed data |
| R11 | **Scope creep stalls v1** (14 pages of future features beckon) | 4 | 3 | **12** | PRD non-goals explicit; roadmap gates each milestone on exit criteria; future features live in 14-future-roadmap.md, not in v1 code | Sprint-start scope check ritual |
| R12 | **Search-engine strategy rate-limited/blocked** (Google blocks automated `site:` queries) | 4 | 2 | 8 | Use a search API (e.g., DuckDuckGo HTML, SearXNG instance, or Brave/Serper API key) rather than scraping Google SERPs; strategy is one of five, not load-bearing | Configurable search backend; skip strategy if unavailable |
| R13 | **Solo-developer bus factor / motivation dips** | 3 | 2 | 6 | Docs-first approach (this set) makes resumption cheap; PROGRESS.md checklist; each milestone independently useful (even M2's CLI alone beats manual checking) | — |

## Top-3 watchlist (reviewed each sprint)

1. **R1/R2 — scraping viability per company.** Tracked concretely: "N of 14 seed companies scannable" is a release criterion (≥12). Measured from M2 onward, weekly.
2. **R6 — silent death.** Any gap > 1 scheduled interval in `scan_runs` is a sev-1 for this product.
3. **R4 — match quality.** Golden-set score in CI + manual precision audit of the first two weeks of real emails.

## Explicitly accepted risks

- Postings that appear and disappear *between* scans (≤ one interval blind spot) — acceptable at 3 scans/day.
- Career pages requiring login (LinkedIn Jobs proper) — out of scope v1 (future roadmap).
- Non-English postings — not handled specially; embeddings degrade gracefully.
