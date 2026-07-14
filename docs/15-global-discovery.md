# LoopJob — Global Discovery Mode (v1 addition)

**Version:** 1.0 · **Status:** Approved direction (added after doc review discussion)

LoopJob is a **two-mode** product:

| Mode | Question it answers | Coverage | Mechanism |
|------|---------------------|----------|-----------|
| **A. Tracked companies** | "Watch *these* companies closely" | Deep & fast for your list | 5-strategy scraping chain (docs 06/07) |
| **B. Global discovery** | "Find matching jobs *anywhere*, by keyword + country" | Broad — the whole indexed job market | Aggregator APIs + ATS sweeps + search sweep |

> **Honesty note (product positioning):** No system can literally guarantee every company in the world. Discovery mode covers the *publicly posted, indexed* job market — which is dramatically beyond any manual search. Coverage is layered so gaps in one source are caught by another.

## 1. Discovery sources (priority order)

1. **Job aggregator APIs** — query with keyword + country, get structured results (title, company, location, posted date, apply link). Primary: **JSearch** (RapidAPI, wraps Google for Jobs) and/or **Adzuna** (free tier, official API, good India coverage). Behind a `DiscoverySource` interface — same pattern as `ScrapeStrategy`.
2. **ATS board sweeps** — Greenhouse (`boards-api.greenhouse.io/v1/boards/{slug}/jobs`), Lever (`api.lever.co/v0/postings/{slug}`), Ashby, SmartRecruiters: uniform public JSON across tens of thousands of companies. Sweep a maintained slug list (seeded from aggregator results + public directories); filter by keyword + country.
3. **Search-engine sweep** — scheduled queries (`software engineer intern 2027 India site:*.myworkdayjobs.com` etc.) via the configured search backend.

Discovered jobs flow into the **same pipeline** as Mode A: normalize → content-hash dedup → match (exclusions → semantic → requirement boost) → email digest. One pipeline, two intakes.

## 2. Data model changes

- `discovery_queries` table: `id, name, keywords text[], country, locations text[], enabled, last_run_at, created_at`. A query row = one saved search ("SWE Intern 2027 · India").
- `jobs.origin` — `tracked` | `discovery`; `jobs.discovery_query_id` FK nullable.
- Companies auto-created from discovery hits get `companies.origin = 'discovered'` (name + apply domain only, no careers_url monitoring unless user promotes them to tracked — one-click "Track this company").
- `settings`: `discovery_enabled`, `discovery_provider` config; API keys env-only (`JSEARCH_API_KEY` / `ADZUNA_APP_ID`+`KEY`).

## 3. API & UI additions

- API: `GET/POST/PATCH/DELETE /discovery/queries`, `POST /discovery/queries/{id}/run` (202), results visible via existing `/jobs?origin=discovery`.
- UI: new **Discovery** page (saved queries board: keywords, country, last run, jobs found; add/edit/run-now), Jobs page gains an Origin filter and a "Track this company" action on discovered jobs.
- Scheduler runs discovery queries in the same scan cycle (after tracked companies).

## 4. Volume & cost controls

Discovery yields far more jobs than 14 tracked companies. Controls: per-query result cap (default 100/run), aggregator pagination cap, country filter applied at the source API (not post-hoc), embedding cache makes matching cost proportional to *new* jobs only, digest groups discovery results in their own email section with a per-digest cap (default 25, "+ N more in dashboard").

## 5. Roadmap placement

New milestone **M5D — Global discovery (4d)** inserted after M5 (email) and before M6 (API complete): DiscoverySource interface + JSearch/Adzuna source + ATS sweep source + `discovery_queries` model/API + pipeline integration. UI lands with M7. Release criterion added: a saved query "Software Engineer Intern · India" returns and matches jobs from companies *not* on the tracked list.
