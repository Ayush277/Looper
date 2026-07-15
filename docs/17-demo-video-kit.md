# LoopJob — Demo Video & Launch Kit

Everything needed to produce a SaaS-style product video, plus landing copy.
Positioning line: **LoopJob — Never miss another internship opening.**

---

## 1. The 60-second demo (main video)

Format: screen recording + voiceover. Shoot at 1920×1080, dark theme (the app is
dark-first — it films beautifully).

| # | Time | On screen | Voiceover |
|---|------|-----------|-----------|
| 1 | 0:00–0:06 | Slow zoom on a Gmail inbox full of nothing. Then hard cut to 14 browser tabs of career portals. | "Every morning, the same ritual. Fourteen career portals. Nothing new. Again." |
| 2 | 0:06–0:12 | Text card, big type on near-black: **"The one day you skip is the day it posts."** | "And the one day you skip… is the day it posts." |
| 3 | 0:12–0:20 | LoopJob **Home** page loads. Stat cards count up: 14 companies, 398 jobs, 21 matched. | "LoopJob is an agent that checks them for you. Three times a day. Forever." |
| 4 | 0:20–0:30 | **Companies** page. Cursor hovers health dots — green, green, red. Click "Add company", type "Rubrik", leave URL blank, hit Add. | "Add a company. Don't know the careers URL? It finds it — Rubrik's board was discovered automatically, ninety-seven jobs, zero configuration." |
| 5 | 0:30–0:40 | **Keywords** page, three columns. Slowly drag-focus each: Include / Requirements / Exclude. | "You describe what you want — not exact strings. It's semantic: 'SDE Intern' matches 'Software Engineer Internship'. And 'Senior' never reaches you." |
| 6 | 0:40–0:50 | **Jobs** page. Scroll matched list. Pause on one card, zoom the reason chips: `Internship 0.91 · Software Engineer 0.87 · Batch 2027`. | "Every match explains itself. No black box — you see exactly why it made the cut." |
| 7 | 0:50–0:57 | The digest email opening in Gmail on a phone. Thumb taps "Apply now →". | "Then it emails you. Company, role, location, and a direct apply link — while it's still fresh." |
| 8 | 0:57–1:00 | Logo mark ◈ on black. Tagline fades in. | "LoopJob. Never miss another internship opening." |

## 2. The 20-second teaser (social cut)

> **0:00** 14 tabs, frantic scrolling. → **0:04** Text: "I stopped checking."
> **0:06** LoopJob Home, numbers counting. → **0:10** Reason chips zoom.
> **0:14** Phone: digest email → Apply tapped. → **0:18** Logo + tagline.

Voiceover (or on-screen text only, for silent autoplay):
"Fourteen portals. Three scans a day. One email — only when it matters."

## 3. Exact things to screen-record

Run `make dev-api` + `make dev-frontend`, open `http://localhost:3777`:

1. **Home** — refresh so cards animate in. (Best B-roll: the stat numbers.)
2. **Companies** — the health-dot column is the money shot: green/amber/red tells the whole reliability story in one frame.
3. **Keywords** — the three-column board reads instantly as "this is how I control it."
4. **Jobs** — hover a matched card; the reason chips are the product's soul.
5. **Statistics** — the funnel bar (398 → 194 excluded → 21 matched) is the single most persuasive visual you have. It proves the filtering is real.
6. **Gmail** — the digest on a phone. Film the tap on "Apply now →".

Pro tip: record at 2× window scale, then slow-pan in post. Never show a cursor
hunting — plan each click before you hit record.

## 4. AI tools that fit this workflow

| Need | Tool | Why |
|------|------|-----|
| Screen recording | **Screen Studio** (Mac) | Auto-zooms to the cursor, smooth motion — the reason most SaaS demos look expensive |
| Voiceover | **ElevenLabs** | Paste the script above; pick a calm, low-key voice (this product is confident, not hyped) |
| Editing / captions | **Descript** | Edit video by editing text; auto-captions for silent autoplay |
| B-roll / title cards | **Runway** or **Pika** | For scene 1–2 abstract shots ("the frantic tab-checking" mood) |
| Music | **Epidemic Sound** / YouTube Audio Library | Minimal, pulsing, no drops. The loop metaphor likes steady rhythm |
| Thumbnail / OG image | **Figma** + a Home-page screenshot | Dark bg, emerald ◈, tagline |

Voice direction: **understated**. The product's promise ("you'll never miss one")
is dramatic enough — don't let the read oversell it.

## 5. Landing page copy (ready to paste)

**Hero**
> # Never miss another internship opening.
> LoopJob watches every company you care about — three times a day, forever — and emails you only the roles that actually fit. With the reason each one matched.
> `[ See it work → ]`

**Three pillars**
> **It adapts.** Career portals block, redirect, and rewrite themselves. LoopJob tries five ways in — careers page, headless browser, hidden job APIs, search index — and remembers what worked.
>
> **It understands.** Not keyword matching. "SDE Intern" matches "Software Engineer Internship"; "University Hiring" matches "Campus Program". Senior roles never reach you.
>
> **It explains.** Every match shows its work: `Internship 0.91 · Software Engineer 0.87 · Batch 2027`. No black box.

**The proof line (use the real funnel)**
> Last run: **398 jobs found → 194 senior roles blocked → 21 worth your morning.**

**Closing**
> Silence means nothing was worth your time. That's the feature.

## 6. Honesty guardrails (don't skip this)

If this video goes public, keep the claims true — it's also just better marketing:

- ✅ "Monitors the companies you add" — true.
- ✅ "Adapts across five strategies" — true.
- ✅ "Semantic matching with reasons" — true, demonstrable on screen.
- ⚠️ **Don't** claim "every company in the world" or "100% of postings." Some portals (Google) forbid crawling in robots.txt, and login-walled boards are out of scope. Current real coverage: 6 of 14 seed companies scan directly.
- ⚠️ **Don't** show real API keys, the Neon connection string, or `.env` on screen. Blur the Settings page's key-status row if it's ever in frame.
- If you show the inbox, blur other senders.

## 7. Shot-list checklist

- [ ] Home stat cards animating (3 takes, pick the smoothest)
- [ ] Companies health column, slow vertical pan
- [ ] Add-company dialog: type "Rubrik", blank URL, Add
- [ ] Keywords three-column board
- [ ] Jobs page: hover → reason chips zoom
- [ ] Statistics funnel bar
- [ ] Phone: digest email → "Apply now →" tap
- [ ] Logo card (◈ emerald on `#0b1020`)
