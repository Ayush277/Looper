# LoopJob — Wireframes

**Version:** 1.0 · **Status:** Draft, pending approval
Low-fidelity structural wireframes (desktop-first, responsive collapse noted per page). Shared shell: fixed left sidebar (icons + labels), top bar with page title + global "Scan now" button + scan-status indicator.

---

## 0. App shell

```
┌────────────┬──────────────────────────────────────────────────────────┐
│  LoopJob   │  {Page title}                    ⟳ Scanning… │ [Scan now] │
│ ─────────  ├──────────────────────────────────────────────────────────┤
│ ◈ Home     │                                                          │
│ ▤ Companies│                                                          │
│ # Keywords │                    {page content}                        │
│ ◷ Scheduler│                                                          │
│ ✉ Email    │                                                          │
│ ▣ Jobs     │                                                          │
│ ≡ History  │                                                          │
│ ⚙ Settings │                                                          │
│ ∿ Stats    │                                                          │
└────────────┴──────────────────────────────────────────────────────────┘
Mobile: sidebar → bottom tab bar (Home, Jobs, Companies, More).
```

## 1. Home

```
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ COMPANIES    │ JOBS FOUND   │ JOBS EMAILED │ LAST SCAN    │ NEXT SCAN    │
│ MONITORED    │ TODAY        │              │              │              │
│    14        │     9        │  4 today     │ 08:00 ✓      │ 14:00        │
│ 1 failing ⚠  │  4 matched   │  63 total    │ completed    │ in 2h 12m    │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
┌───────────────────────────────────────────────┬──────────────────────────┐
│ RECENT MATCHES                                │ NEEDS ATTENTION          │
│ ┌───────────────────────────────────────────┐ │ ⚠ Cisco — 3 failed       │
│ │ Nvidia · SWE Intern 2027 · Bangalore      │ │   crawls since Jul 11    │
│ │ matched: Internship, SWE, Batch 2027      │ │   [Verify URL] [Pause]   │
│ │ 2h ago                    [Apply ↗] [🔖]  │ │                          │
│ ├───────────────────────────────────────────┤ │ ✉ Last email: sent ✓     │
│ │ Google · Software Eng Intern · Hyderabad  │ │   08:05 to prince…@…     │
│ └───────────────────────────────────────────┘ │                          │
└───────────────────────────────────────────────┴──────────────────────────┘
```

## 2. Companies

```
[+ Add company]                                    Search: [_________]  Filter: (Active ▾)
┌──────────────────────────────────────────────────────────────────────────────┐
│ COMPANY    HEALTH      LAST SUCCESS   STRATEGY      JOBS   STATUS    ACTIONS  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Google     ● healthy   today 08:02    job_api       42/7   active   [Scan][⋮] │
│ Nvidia     ● healthy   today 08:03    careers_page  18/3   active   [Scan][⋮] │
│ Cisco      ● failing   Jul 11 20:04   —             12/1   active   [Scan][⋮] │
│ Rubrik     ◐ degraded  today 08:04    search_eng     4/1   active   [Scan][⋮] │
│ Oracle     ● healthy   today 08:02    careers_page  29/2   paused   [Resume]  │
└──────────────────────────────────────────────────────────────────────────────┘
[⋮] menu: Verify URL · Edit · Pause/Resume · Delete
Row click → detail drawer: URL + verified badge, crawl history (last 10 with
strategy/duration/error), jobs from this company, notes.

Add-company dialog:
┌─────────────────────────────────────┐
│ Add company                         │
│ Name*        [Rubrik            ]   │
│ Careers URL  [https://…  (opt.) ]   │
│              (blank = auto-discover)│
│          [Cancel]  [Add & verify]   │
└─────────────────────────────────────┘
```

## 3. Keywords

```
Three-column board (stacks vertically on mobile):
┌── INCLUDE (match) ──────┬── REQUIREMENTS (boost) ──┬── EXCLUDE (block) ────┐
│ [+ add]                 │ [+ add]                  │ [+ add]               │
│ ⦿ Software Engineer  ✕ │ ⦿ 2027               ✕  │ ⊘ Senior           ✕ │
│ ⦿ SDE                ✕ │ ⦿ Batch 2027         ✕  │ ⊘ Principal        ✕ │
│ ⦿ Backend            ✕ │ ⦿ Final Year         ✕  │ ⊘ Manager          ✕ │
│ ⦿ Machine Learning   ✕ │ ⦿ India              ✕  │ ⊘ Staff            ✕ │
│ ⦿ Intern             ✕ │ ⦿ Bangalore          ✕  │ ⊘ 5+ Years         ✕ │
│ …                       │ …                        │ …                     │
└─────────────────────────┴──────────────────────────┴───────────────────────┘
ℹ Matching is semantic: "SDE Intern" will match "Software Engineer Internship".
  Excludes are hard blocks. Changes apply from the next scan.
```

## 4. Scheduler

```
┌── SCAN TIMES (Asia/Kolkata ▾) ──────────────────────────┐
│  08:00  [enabled ✓]  next: tomorrow 08:00      [✎][✕]   │
│  14:00  [enabled ✓]  next: today 14:00         [✎][✕]   │
│  20:00  [enabled ✓]  next: today 20:00         [✎][✕]   │
│  [+ Add time]                                           │
└─────────────────────────────────────────────────────────┘
┌── STATUS ───────────────────────────────────────────────┐
│ Scheduler: ● running    Last run: today 08:00 (✓ 14/14) │
│ Next run: today 14:00                                   │
└─────────────────────────────────────────────────────────┘
```

## 5. Email Settings

```
┌── NOTIFICATIONS ────────────────────────────────────────┐
│ Email digest      [ on ⭘──]                             │
│ Recipient         [prince908ayush@gmail.com        ]    │
│ Provider          Resend  (API key: ✓ configured)       │
│                   [Send test email]                     │
├── PREVIEW ──────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐         │
│ │ LoopJob — 4 new internship matches          │         │
│ │ ── Google ────────────────────────────      │         │
│ │ Software Engineering Intern, 2027           │         │
│ │ Hyderabad · Posted Jul 13    [Apply →]      │         │
│ │ Matched: Internship · SWE · Batch 2027      │         │
│ └─────────────────────────────────────────────┘         │
├── FUTURE CHANNELS ──────────────────────────────────────┤
│ Telegram / Discord / Slack / Push     (coming soon)     │
└─────────────────────────────────────────────────────────┘
```

## 6. Jobs Found

```
Search [software intern____]  Company (All ▾)  Status (Matched ▾)  Location (All ▾)
Date (Last 30 days ▾)  Keyword (All ▾)                      132 jobs · page 1/6
┌──────────────────────────────────────────────────────────────────────────────┐
│ ● Nvidia — Software Engineering Intern, 2027                    score 0.89   │
│   Bangalore · Posted Jul 13 · found today 08:03 · ✉ emailed                  │
│   Matched: Internship (0.91) · Software Engineer (0.87) · Batch 2027         │
│   [Apply ↗]   [✓ Mark applied]   [🔖 Bookmark]                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ ● Google — Software Engineer Intern (Hyderabad)                score 0.86    │
│   …                                                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│ ○ Amazon — Senior SDE, Alexa   (excluded: "Senior")           [show why]    │
└──────────────────────────────────────────────────────────────────────────────┘
Tabs: All · Matched · Bookmarked 🔖 · Applied ✓ · Excluded
```

## 7. History

```
┌── SCAN RUNS ─────────────────────────────────────────────────────────────────┐
│ WHEN            TRIGGER    COMPANIES   NEW JOBS  MATCHED  EMAIL   STATUS      │
├──────────────────────────────────────────────────────────────────────────────┤
│ today 08:00     scheduled  13✓ 1✗      6         4        sent ✓  completed ⚠│
│ yesterday 20:00 scheduled  14✓         2         0        —       completed  │
│ yesterday 14:00 manual     14✓         0         0        —       completed  │
└──────────────────────────────────────────────────────────────────────────────┘
Row expand → per-company: strategy used, attempts, duration, jobs found, error text.
```

## 8. Settings

```
┌── MATCHING ─────────────────────────────────────────────┐
│ Match threshold        [0.55 ────●────── ]              │
│ Requirement boost      [0.05]                           │
│ Embedding provider     (OpenAI ▾)  key: ✓ via env       │
├── SCANNING ─────────────────────────────────────────────┤
│ Parallel companies     [4 ▾]                            │
│ Per-domain delay       [2 s]                            │
│ Retry attempts         [3]                              │
├── SYSTEM ───────────────────────────────────────────────┤
│ Timezone               (Asia/Kolkata ▾)                 │
│ Raw-payload retention  [30 days]                        │
│ ● API ✓  ● DB ✓  ● Redis ✓  ● Worker ✓  (deep health)   │
└─────────────────────────────────────────────────────────┘
```

## 9. Statistics

```
Range: (Last 30 days ▾)
┌── Jobs found vs matched (line/area) ────────────────────────────────┐
│  ▂▃▅▂▇▃▂▅…                                                          │
└─────────────────────────────────────────────────────────────────────┘
┌── Per-company yield (bar) ───────────┬── Crawl success rate (line) ─┐
│ Google ████████ 42                   │ 97% ▔▔▔▔▔╲▔▔▔                │
│ Oracle ██████ 29 …                   │                              │
└──────────────────────────────────────┴──────────────────────────────┘
┌── Funnel ───────────────────────────────────────────────────────────┐
│ Found 132 → Passed exclusions 97 → Matched 41 → Emailed 41 → Applied 12 │
└─────────────────────────────────────────────────────────────────────┘
```

## Email digest wireframe

```
Subject: LoopJob: 4 new internship matches (Google, Nvidia +1)

┌────────────────────────────────────────────┐
│  ◈ LoopJob            4 new matches        │  ← header, brand color
├────────────────────────────────────────────┤
│  GOOGLE                                    │
│  Software Engineering Intern, 2027         │  ← title, bold, links to job
│  📍 Hyderabad, India   ·  Posted Jul 13    │
│  Matched because:                          │
│   • Internship  • Software Engineer        │
│   • Batch 2027                             │
│  [ Apply now → ]                           │  ← button, direct link
├────────────────────────────────────────────┤
│  NVIDIA                                    │
│  …                                         │
├────────────────────────────────────────────┤
│  Scanned 14 companies at 08:00 IST         │
│  View all in dashboard →                   │  ← footer
└────────────────────────────────────────────┘
Single column, ≤600px, table-based layout, inline CSS (email-client-safe),
plaintext alternative included.
```
