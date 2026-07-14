# LoopJob — Future Roadmap (post-v1)

**Version:** 1.0 · **Status:** Draft, pending approval
Everything here is **explicitly out of v1 scope** (PRD §3). Sequenced by leverage-per-effort against the core mission: *apply to the right internships faster than anyone else.*

---

## Horizon 1 — Deepen the pipeline (v1.x, weeks after launch)

| Feature | What | Why now | Builds on |
|---------|------|---------|-----------|
| **ATS adapters** | First-class strategies for Greenhouse, Lever, Workday, Ashby, SmartRecruiters, SuccessFactors — most are stable JSON APIs (`boards-api.greenhouse.io`, `api.lever.co`…) | Converts the flakiest scraping into the most reliable; one adapter unlocks *every* company on that ATS | ScrapeStrategy interface (D4) — each adapter is one new module |
| **Telegram notifier** | Instant push per match (not just digest) | Latency: Telegram beats email refresh; trivial Bot API | Notifier interface (FR-7.6) |
| **Discord / Slack notifiers** | Webhook posts | Same interface, near-zero cost | Notifier interface |
| **Re-match action** | Button to re-run matching over stored jobs after keyword/threshold changes | Removes the "new keywords only apply forward" limitation | Jobs already store embeddings |
| **AI summaries** | LLM one-liner per job in email/dashboard ("2027 SWE intern, Bangalore, CS fundamentals + one systems language, apply by Aug 1") | Faster triage; deadline extraction is high-value | Description snippets already stored |

## Horizon 2 — From finder to tracker (v2)

| Feature | What | Notes |
|---------|------|-------|
| **Application tracker** | Statuses beyond applied: OA → interview → offer/reject; notes, dates, reminders | `user_state` grows into an `applications` table; kanban view |
| **Resume auto-match score** | Embed resume; score each job against it; sort by fit | Same embedding infra; resume upload + parsing (PDF) |
| **LinkedIn support** | LinkedIn Jobs search integration | Login-walled + aggressive anti-bot → likely via official-ish feeds or manual-import; kept out of v1 deliberately (R10) |
| **Web push notifications** | Browser push for matches | Service worker in Next.js; Notifier interface again |
| **Multi-user / auth** | Real accounts, per-user companies/keywords/emails | Schema already keys cleanly; add `user_id` FKs + auth (Clerk/Auth.js); turns LoopJob into an actual SaaS |

## Horizon 3 — Apply-side automation (v3, ambitious)

| Feature | What | Risk/notes |
|---------|------|------------|
| **Chrome extension** | On any careers page: shows LoopJob match verdict, one-click save, mark-applied sync | Manifest v3; talks to LoopJob API |
| **Resume tailoring** | LLM drafts a job-specific resume bullet/cover paragraph diff from your base resume | Human-in-the-loop always; never auto-submit |
| **Auto-fill applications** | Pre-fill Workday/Greenhouse forms from a profile vault | High fragility + ethical line: *assist*, never submit without explicit user action per application |
| **Referral tracking** | Track referral requests per company (who, when, status) alongside applications | Simple CRM-lite table |

## Sequencing rationale

1. **Reliability before reach** (H1 ATS adapters first): more trustworthy data beats more features on flaky data.
2. **Speed of action** (notifiers, summaries): the product's edge is time-to-apply.
3. **Own the funnel** (tracker, resume score): once discovery is solved, the bottleneck moves to managing applications — follow it.
4. **Automation last**: apply-side automation only after the data layer has proven itself, and always human-confirmed.

## Non-goals (still)

- Mass-scraping or reselling job data — LoopJob stays a personal agent.
- Auto-submitting applications end-to-end — assist, never impersonate.
- Circumventing logins/CAPTCHAs — hard line regardless of feature pressure.
