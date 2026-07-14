# LoopJob — User Guide: How It Works, Settings, and Real Deployment

## 1. How LoopJob works (the loop)

```
Scheduler (8:00 / 14:00 / 20:00 IST, editable)
   └─▶ SCAN: every active company, in order of what worked last time:
         1. careers page (static fetch → Playwright browser if JS-heavy)
         2. hidden job APIs (Workday/Greenhouse/Lever/Ashby/SmartRecruiters + Amazon/Microsoft adapters)
         3. search index (JSearch — pending correct endpoint)
         4. wider search  5. LLM extraction (future)
   └─▶ DEDUP: each job hashed (company+title+location+URL) — seen once, stored once, forever
   └─▶ MATCH: new jobs only
         • hard exclusions first (Senior, Staff, "5+ years"…) — these can NEVER email you
         • semantic similarity vs your include keywords (AI embeddings — "SDE Intern" ≈ "Software Engineer Internship")
         • requirement boosts (2027, Bangalore/Bengaluru, India, Remote…)
         • score ≥ threshold → MATCHED, with human-readable reasons
   └─▶ EMAIL: one digest per scan, only never-before-emailed matches, via Resend
   └─▶ DASHBOARD: everything visible at localhost:3000 (Home/Jobs/Companies/…)
```

## 2. Running it day-to-day (on this Mac)

```bash
cd ~/LoopJob
make dev-api        # terminal 1 — API + scheduler (must stay running for scans to fire)
make dev-frontend   # terminal 2 — dashboard at http://localhost:3000
```
Keep terminal 1 running (laptop awake) and scans fire automatically. Or click **Scan now** on Home anytime.

## 3. Changing settings — all from the dashboard

| Page | What you change there |
|------|----------------------|
| **Companies** | Add a company (name + careers URL — URL optional, ATS boards are auto-discovered) · Pause/Resume · per-company Scan · Delete. Health dot: green=working, amber=1–2 failures, red=3+ (needs attention). |
| **Keywords** | Three lists. *Include* = what you want (semantic, variants match). *Requirements* = eligibility/location (boost score + show in reasons). *Exclude* = hard blocks (never emailed). Changes apply from the next scan. |
| **Scheduler** | Add/remove scan times. Takes effect immediately, no restart. |
| **Email** | Recipient address, digest on/off. Provider status shows if the Resend key is loaded. |
| **Settings** | **Match threshold** (0.55 default): lower → more matches + more noise; raise to 0.60+ if you get junk, drop to 0.50 if you miss things. **Requirement boost** per hit. **Scan concurrency**. |
| **Jobs** | Not a setting, but your workflow: Apply ↗ → Mark applied / Bookmark. Check the *Excluded/All* tabs occasionally — if a good job sits in "unmatched", add a keyword or lower the threshold. |
| **History / Statistics** | Audit every scan (which strategy, errors) and tune from the funnel. |

Secrets (API keys) are NEVER in the dashboard — only in `backend/.env`:
`RESEND_API_KEY` (emails) · `JSEARCH_API_KEY` (search/discovery) · `OPENAI_API_KEY` (optional, better embeddings; local model used otherwise). Restart the API after editing `.env`.

## 4. Deploying for real use (runs 24/7 without your laptop)

**Recommended: Railway (~$5–10/mo).** I cannot create the account for you — steps:

1. Sign up at railway.app → **New Project → Deploy from GitHub repo** (push this repo to GitHub first: create an empty repo, then `git add -A && git commit -m "LoopJob v1" && git remote add origin <url> && git push -u origin main`).
2. Add **PostgreSQL** and **Redis** plugins to the project (one click each).
3. Create two services from the repo:
   - **api** — root `backend/`, Dockerfile detected. Env vars: `LOOPJOB_ENV=prod`, `DATABASE_URL=${{Postgres.DATABASE_URL}}` (change scheme to `postgresql+asyncpg://`), `REDIS_URL=${{Redis.REDIS_URL}}`, `RESEND_API_KEY`, `JSEARCH_API_KEY`. Pre-deploy command: `alembic upgrade head`. Then run `python -m app.db.seed` once via Railway shell.
   - **frontend** — root `frontend/`, build arg `NEXT_PUBLIC_API_URL=https://<api-domain>/api/v1`.
4. Generate public domains for both services (Settings → Networking).
5. Set `FRONTEND_ORIGIN=https://<frontend-domain>` on the api service (CORS).
6. Verify: open `https://<api-domain>/api/v1/health/deep` (all green) → open the frontend → Scan now → digest lands in Gmail.
7. Optional hardening: put the frontend behind Railway's private networking + a basic-auth proxy, and add a healthchecks.io ping so you're alerted if a scheduled scan is ever missed (see docs/13).

**Email deliverability:** digests currently send from `onboarding@resend.dev` (fine for personal use, may hit spam initially — mark "Not spam" once). For a custom sender, verify a domain in the Resend dashboard (SPF+DKIM) and change the sender in `app/notifications/senders.py`.

**Alternative deploys:** any Docker host works — `docker compose up` on a $4 VPS gives you the whole stack (docs/13 has the full strategy; Render/AWS paths included).

## 5. Maintenance (15 min/month)

- Red health dot on a company → open History, read the error → usually the careers URL moved: edit it on Companies.
- Inbox too noisy → raise threshold, add Exclude keywords. Too quiet → check Jobs → All tab, lower threshold, add Include keywords.
- Keys leak/rotate → edit `.env` (or Railway env vars) and restart. Note: the keys you pasted in chat should be treated as shared — rotating them in the Resend/RapidAPI dashboards is good hygiene.
