# LoopJob — User Personas & User Stories

**Version:** 1.0 · **Status:** Draft, pending approval

---

## Part A — Personas

Although LoopJob v1 is single-user, designing against distinct personas keeps the product honest about different *modes of use* — and future-proofs it for multi-user SaaS.

### P1 — "Ayush" · The Final-Year Applicant (primary)

| | |
|---|---|
| **Profile** | Final-year B.Tech CS student, Batch 2027, based in India |
| **Goal** | Land a SWE internship at a top product company; apply within hours of a posting going live |
| **Tech comfort** | High — can run Docker, read logs, tweak configs |
| **Pain today** | Checks 14 career portals manually; misses postings with odd titles; forgets on busy days |
| **Needs from LoopJob** | Set-and-forget monitoring; high-precision matches; a *reason* attached to every match so he can trust it; direct apply link |
| **Frustrations to avoid** | Duplicate emails, spammy irrelevant matches (Senior roles), silent failures |

### P2 — "Priya" · The Busy Parallel-Tracker (secondary)

| | |
|---|---|
| **Profile** | Same cohort, juggling coursework + interview prep; low tolerance for tooling upkeep |
| **Goal** | Glance at one email 3×/day; never open a career portal again |
| **Tech comfort** | Medium — will use the dashboard, won't read logs |
| **Needs** | Email that is skimmable in 20 seconds; dashboard health warnings in plain language ("Cisco hasn't been scanned successfully in 3 days — verify its URL") |

### P3 — "The Operator" · Ayush wearing his maintainer hat (tertiary)

| | |
|---|---|
| **Profile** | The same user, monthly maintenance mode |
| **Goal** | Keep the crawler fleet healthy with < 15 min/month of effort |
| **Needs** | Per-company health status, crawl history, error surfacing, one-click URL verification, easy pause/resume |

---

## Part B — User stories

Format: *As a \<persona>, I want \<capability>, so that \<outcome>.* Priority: **P0** = v1 must-have, **P1** = v1 should-have, **P2** = future.

### Epic 1 — Company management

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-1.1 | As Ayush, I want to add a company by name (and optionally its careers URL), so that it enters the monitoring loop. | P0 | Company appears in list; if no URL given, system attempts discovery; duplicate names rejected. |
| US-1.2 | As Ayush, I want to verify a company's career URL from the dashboard, so that I know crawling will work before waiting for a scan. | P0 | "Verify" triggers a live fetch; result (reachable / jobs detected / blocked / 404) shown within 30 s. |
| US-1.3 | As Ayush, I want to pause and resume a company, so that dead or irrelevant companies stop consuming scans without losing their history. | P0 | Paused companies are skipped by the scheduler; badge shows "Paused"; resume restores scanning. |
| US-1.4 | As Ayush, I want to delete a company, so that my list stays clean. | P0 | Soft-delete; associated jobs retained in history, flagged as from a removed company. |
| US-1.5 | As the Operator, I want per-company health status (healthy / degraded / failing) and last-successful-crawl time, so that I can spot broken scrapers at a glance. | P0 | Health computed from recent crawl outcomes; failing companies visually flagged on the Companies page and Home. |

### Epic 2 — Filters & keywords

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-2.1 | As Ayush, I want to manage include keywords (Software Engineer, Backend, ML…), so that matching targets my interests. | P0 | CRUD via dashboard; changes apply from the next scan. |
| US-2.2 | As Ayush, I want to manage requirement keywords (2027, Final Year, India, Remote, Bangalore…), so that matches are boosted/filtered by eligibility and location. | P0 | Stored as a distinct keyword class; surfaced in match reasons. |
| US-2.3 | As Ayush, I want to manage exclusion keywords (Senior, Principal, Staff, 5+ Years…), so that unwanted roles never reach my inbox. | P0 | A job hitting a hard exclusion is stored but never marked as matched or emailed. |
| US-2.4 | As Ayush, I want matching to be semantic, not literal, so that "SDE Intern" matches my "Software Engineer Internship" keyword. | P0 | Embedding-similarity matching demonstrated by test suite on a fixture set of title variants. |
| US-2.5 | As Ayush, I want each match to carry human-readable reasons ("Matched: Internship, Software Engineer, Batch 2027"), so that I trust the system. | P0 | Reasons stored per job; shown in email and dashboard. |

### Epic 3 — Scanning & scraping

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-3.1 | As Ayush, I want each company scanned via an adaptive strategy chain (careers page → job API → search engine → LLM extraction), so that one brittle scraper never blinds me. | P0 | Strategy attempted in priority order; the first success wins; chosen strategy recorded per crawl. |
| US-3.2 | As Ayush, I want JS-heavy portals (Workday-style) handled, so that companies like Nvidia/Cisco aren't unscannable. | P0 | Playwright fallback renders and extracts where httpx fails. |
| US-3.3 | As the Operator, I want scraping to retry with backoff, rotate user agents, and throttle, so that transient blocks don't cause permanent failures. | P0 | Configurable retry/backoff; per-domain rate limit; failures logged with cause. |
| US-3.4 | As Ayush, I want a "Scan now" button (global and per-company), so that I don't wait for the next cron slot when testing. | P0 | Triggers an immediate background scan; UI shows progress state. |
| US-3.5 | As Ayush, I want pagination and infinite scroll handled, so that jobs beyond page 1 are found. | P1 | Strategy walks pagination up to a configurable page/scroll cap. |

### Epic 4 — Scheduling

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-4.1 | As Ayush, I want to configure scan times (e.g., 08:00, 14:00, 20:00 IST), so that scans align with my routine. | P0 | Times editable in dashboard; scheduler picks up changes without restart; timezone-aware. |
| US-4.2 | As Ayush, I want to see last-scan and next-scan times on the Home page, so that I know the loop is alive. | P0 | Both timestamps accurate to the configured timezone. |
| US-4.3 | As the Operator, I want a missed scan (downtime at trigger time) to be visible in History, so that gaps are explainable. | P1 | Scan runs recorded with status: completed / failed / skipped. |

### Epic 5 — Matching & notification

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-5.1 | As Ayush, I want at most one email per scan run containing only NEW matches, so that my inbox stays clean. | P0 | No email when zero new matches; digest groups jobs by company. |
| US-5.2 | As Ayush, I want each email row to show company, title, location, posted date, direct apply link, and match reasons, so that I can act without opening the dashboard. | P0 | All six fields present; apply link goes directly to the posting. |
| US-5.3 | As Ayush, I want a job to be emailed at most once ever, so that re-crawls don't spam me. | P0 | Dedup by content hash; `email_sent` flag checked before send. |
| US-5.4 | As Ayush, I want the email to be clean and beautiful, so that it's pleasant to read on mobile. | P0 | Responsive HTML template; passes render checks in Gmail mobile/desktop. |
| US-5.5 | As Priya, I want future notification channels (Telegram/Discord/Slack/push), so that I'm reached where I live. | P2 | Notification layer is an interface; email is the v1 implementation. |

### Epic 6 — Dashboard & job tracking

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-6.1 | As Ayush, I want a Home page with cards (companies monitored, jobs found today, jobs emailed, last scan, next scan), so that I get the pulse in 5 seconds. | P0 | Cards live-accurate; auto-refresh. |
| US-6.2 | As Ayush, I want a Jobs page with search + filters (company, date, keyword, location), so that I can review everything found. | P0 | Server-side filtering + pagination. |
| US-6.3 | As Ayush, I want to mark a job Applied and to Bookmark jobs, so that LoopJob doubles as a light application tracker. | P0 | Status persisted; filterable by status. |
| US-6.4 | As Ayush, I want a History page of scan runs (when, what strategy, jobs found, errors), so that I can audit behavior. | P1 | Paginated run log with per-company drill-down. |
| US-6.5 | As Ayush, I want a Statistics page (jobs/company, matches over time, email volume, crawl success rate), so that I can tune my setup. | P1 | Charts over selectable time ranges. |
| US-6.6 | As Ayush, I want Email Settings (recipient, digest on/off) and general Settings editable in the UI, so that config doesn't require env edits. | P0 | Persisted in DB; secrets (API keys) remain env-only. |
