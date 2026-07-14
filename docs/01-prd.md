# LoopJob — Product Requirements Document (PRD)

**Version:** 1.0 · **Date:** 2026-07-14 · **Status:** Draft, pending approval
**Owner:** Ayush (single user & operator)

---

## 1. Problem statement

Students applying for Software Engineering internships must manually check dozens of company career portals daily. Openings for competitive programs (e.g., "SDE Intern, Batch 2027, Bangalore") often fill within days — sometimes hours — of posting. Manual checking is:

- **Slow** — 14+ portals × several minutes each, every day.
- **Error-prone** — portals use inconsistent titles ("SDE Intern", "University Grad Program", "Campus Hire"), so relevant roles are missed.
- **Unreliable** — checks are skipped on busy days, exactly when a posting might appear.

Job aggregators (LinkedIn, Naukri) are noisy, delayed, and miss postings that only appear on official career pages.

## 2. Product vision

LoopJob is a personal, always-on job-watch agent. The user configures a list of companies and a set of match/exclude filters once. LoopJob then:

1. **Crawls** each company's careers portal on a user-defined schedule (e.g., 8 AM / 2 PM / 8 PM).
2. **Adapts** its scraping strategy per company (official page → job API → search engine → LLM extraction).
3. **Matches semantically** — "Software Development Engineer Intern" matches "Software Engineer Internship"; "University Hiring" matches "Campus Hiring" — using embeddings plus rule-based exclusions.
4. **Deduplicates** via content hashing so a job is emailed at most once.
5. **Emails** a clean digest with company, title, location, posting date, direct apply link, and *why it matched*.
6. Exposes a **dashboard** for configuration, job history, health monitoring, and statistics.

## 3. Goals & non-goals

### Goals (v1)

| # | Goal | Success signal |
|---|------|----------------|
| G1 | Detect new internship postings within one scan cycle of them appearing | New posting appears in dashboard + email at the next scheduled scan |
| G2 | Zero duplicate email notifications | A given job hash triggers ≤ 1 email, ever |
| G3 | Semantic matching beats keyword matching | Variant titles ("SDE Intern" vs "Software Engineer Internship") are matched; senior roles are excluded |
| G4 | Fully autonomous operation | Runs 7 days unattended with no missed scheduled scans |
| G5 | Per-company health visibility | Dashboard shows last successful crawl and failure state per company |
| G6 | Global discovery — find matching jobs beyond the tracked list, by keyword + country ([details](15-global-discovery.md)) | A saved query ("SWE Intern · India") surfaces matched jobs from companies not on the tracked list |

### Non-goals (v1)

- Auto-applying or auto-filling applications (future).
- Resume matching/tailoring (future).
- Multi-user accounts / true multi-tenant SaaS (single-user, but architected so auth can be added).
- Telegram/Discord/Slack/push notifications (email only in v1; notification layer is pluggable).
- ATS-specific integrations beyond what generic strategies cover (Greenhouse/Lever/Workday adapters are future work, though the strategy interface must accommodate them).

## 4. Target user

A single power user: a final-year CS student (Batch 2027) in India applying to SWE internships at large tech companies. Technically proficient; can self-host with Docker; wants signal, not noise. (Full personas in [02-personas-user-stories.md](02-personas-user-stories.md).)

## 5. Core user journey

1. **Setup (once, ~10 min):** Add companies (name + optional careers URL — LoopJob discovers/verifies the URL). Configure include keywords, requirement keywords (2027, Final Year…), locations, and exclusion keywords (Senior, Staff, 5+ Years…). Set scan times and notification email.
2. **Steady state (zero-touch):** Scheduler fires at configured times → all active companies are scanned in parallel → new jobs are matched, scored, stored → one digest email per scan containing only *new* matches.
3. **Act on a match:** Open email → click direct apply link → apply → mark as "Applied" in dashboard (or bookmark for later).
4. **Maintain (occasional):** Dashboard flags unhealthy companies (crawl failing N times). User verifies/fixes the career URL, pauses dead companies, tunes keywords when noise appears.

## 6. Feature summary

| Area | v1 scope |
|------|----------|
| **Companies** | CRUD, pause/resume, career-URL verification, health status, last-crawl time |
| **Scraping** | Static HTML (httpx + BeautifulSoup), JS rendering (Playwright), pagination, infinite scroll, JSON APIs, sitemaps, RSS, embedded structured data (JSON-LD); per-company strategy selection with fallback chain; retries, rotating user agents, throttling, robots.txt awareness |
| **Search fallback** | Search-engine queries (`site:careers.google.com software engineer internship`) when direct crawl fails or yields nothing |
| **Matching** | Embedding similarity (OpenAI `text-embedding-3-small`, local sentence-transformers fallback) + hard exclusion rules + requirement boosting; per-job match reasons |
| **Dedup** | SHA-256 hash over normalized (company, title, location, apply-URL path) |
| **Scheduler** | User-configured times (cron), manual "Scan now", per-company and global |
| **Email** | Resend; responsive HTML digest; company/title/location/date/link/match-reasons |
| **Dashboard** | Home (stat cards), Companies, Keywords, Scheduler, Email Settings, Jobs Found, History, Settings, Statistics |
| **Jobs page** | Search + filters (company/date/keyword/location), Apply button, Mark Applied, Bookmark |
| **Quality** | Structured logging, retries with backoff, rate limiting, Redis caching, typed config from env, tests, full type safety (TypeScript + Python type hints), consistent error handling |

## 7. Success metrics

| Metric | Target |
|--------|--------|
| Scan reliability | ≥ 99% of scheduled scans execute |
| Company coverage | ≥ 12 of the 14 seed companies scannable via some strategy |
| Match precision (manual audit) | ≥ 85% of emailed jobs are genuinely relevant |
| Match recall (spot check vs. manual portal check) | ≥ 90% of relevant postings caught |
| Duplicate emails | 0 |
| Time from posting to email | ≤ 1 scan interval |
| Full scan wall time (14 companies) | ≤ 10 minutes |

## 8. Constraints & assumptions

- **Personal use, single user** — no auth wall required in v1 (but API keys/secrets still handled properly; deployment may sit behind basic auth).
- **Budget-conscious** — embeddings cached aggressively; local sentence-transformers as zero-cost fallback; free/cheap hosting tiers (Railway/Render).
- **Polite scraping** — throttled, off-peak-scheduled, robots.txt respected where appropriate; this is personal-scale (14 companies × 3 scans/day), not bulk harvesting.
- **Portals change** — scraping strategies WILL break; the system must degrade gracefully (fallback chain + health flags), never silently.

## 9. Release criteria (v1 "done")

- All 14 seed companies configured; ≥ 12 return jobs on scan.
- Scheduled scans run at 8 AM / 2 PM / 8 PM IST for 7 consecutive days without manual intervention.
- Digest emails delivered with correct match reasons; zero duplicates across the week.
- Dashboard fully functional across all 9 pages; mobile-usable.
- Test suite green; Docker Compose brings up the full stack with one command.
