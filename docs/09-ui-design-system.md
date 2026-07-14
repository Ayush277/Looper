# LoopJob — UI Design System

**Version:** 1.0 · **Status:** Draft, pending approval
**Stack:** TailwindCSS v4 + shadcn/ui (Radix primitives) · dark & light themes · desktop-first, mobile-responsive

---

## 1. Design principles

1. **Glanceable** — the Home page answers "is the loop alive, did I get matches?" in 5 seconds. Numbers big, chrome small.
2. **Calm by default, loud on exceptions** — neutral surfaces; color reserved for health states and matches. A failing crawler should be the most visible thing on screen.
3. **Every claim explains itself** — match scores expand into reasons; health badges expand into crawl errors. No black boxes.
4. **Dense but breathable** — tables for operators (Companies, History), cards for consumption (Home, Jobs).

## 2. Brand

- **Name:** LoopJob · **Tagline:** *Never miss another internship opening.*
- **Logo concept:** `◈` loop/orbit mark — a circular arrow forming an "L"-negative-space; favicon = the mark alone.
- **Voice:** direct, technical, quietly confident. ("Cisco hasn't been crawled successfully since Jul 11 — verify its URL." Not "Oops! Something went wrong 😢".)

## 3. Color tokens

Defined as CSS variables (shadcn convention), HSL. Dark theme is the default (this is a tool checked at 8 AM and 8 PM).

| Token | Dark (default) | Light | Use |
|-------|----------------|-------|-----|
| `--background` | `222 47% 6%` | `0 0% 100%` | App background |
| `--card` | `222 44% 9%` | `210 20% 98%` | Cards, tables |
| `--border` | `220 30% 16%` | `214 20% 90%` | Hairlines |
| `--foreground` | `210 30% 96%` | `222 47% 10%` | Primary text |
| `--muted-foreground` | `217 15% 62%` | `220 10% 42%` | Secondary text |
| `--primary` | `160 84% 45%` | `161 90% 30%` | Brand emerald — actions, links, the "match" color |
| `--primary-foreground` | `222 47% 6%` | `0 0% 100%` | Text on primary |
| `--accent` | `217 91% 62%` | `221 83% 47%` | Info accents, charts secondary |
| `--destructive` | `0 72% 54%` | `0 74% 46%` | Failing health, destructive actions |
| `--warning` | `38 92% 55%` | `32 95% 40%` | Degraded health, attention |
| `--success` | `160 84% 45%` | `161 90% 30%` | = primary (healthy, sent, applied) |
| `--ring` | `160 84% 45%` | same | Focus rings |

**Semantic mapping:** healthy ● emerald · degraded ◐ amber · failing ● red · paused ○ gray · matched = emerald left-border on cards · excluded = gray, struck subtly.

Charts (Recharts): series order `primary`, `accent`, amber, purple `271 81% 66%`; never rely on color alone (direct labels/legends).

## 4. Typography

| Role | Font | Size/weight |
|------|------|-------------|
| UI text | **Inter** (variable) | 14px/400 body · 13px/400 secondary |
| Numbers & stats | **Inter** tabular-nums | Stat cards 30px/700; table numerics `font-variant-numeric: tabular-nums` |
| Headings | Inter | H1 22px/600 (page title) · H2 16px/600 (section) · overline labels 11px/600 uppercase tracking-wide muted |
| Code/IDs/URLs | **JetBrains Mono** | 12.5px |

Line-height 1.5 body, 1.2 headings. Self-hosted via `next/font` (no external font requests).

## 5. Spacing, layout, radius

- **Grid:** 4px base scale (Tailwind default). Page gutter 24px; card padding 20px; table cell 12px×16px.
- **Layout:** sidebar 232px fixed (collapses to icon rail ≤1100px, bottom tabs ≤640px); content max-width 1280px.
- **Radius:** `--radius: 10px` cards/dialogs; 8px buttons/inputs; 999px badges/pills.
- **Elevation:** borders over shadows; single soft shadow (`0 1px 2px rgb(0 0 0 / .25)`) on popovers/dialogs only.

## 6. Core components (shadcn/ui base + LoopJob variants)

| Component | Base | LoopJob usage |
|-----------|------|---------------|
| **StatCard** | Card | Overline label + 30px number + delta/sub-line + optional warning chip. Home page. |
| **HealthBadge** | Badge | Dot + word (`● healthy`). Tooltip shows last error + last success time. |
| **JobCard / JobRow** | Card / Table row | Title (link) · company · location · posted/found dates · score chip · reason chips · actions (Apply ↗ primary, Mark applied, Bookmark). Emerald left border when matched. |
| **ReasonChip** | Badge (outline) | `Internship 0.91` for include hits, plain `Batch 2027` for requirements. Max 4 shown + "+2 more". |
| **CompanyTable** | DataTable (TanStack Table) | Sortable, row-click drawer, sticky header. |
| **ScanButton** | Button | Global top-bar; morphs into progress pill (`⟳ 9/14`) while a run is live. |
| **TimeSlotEditor** | Custom + Select | Hour/minute picker rows on Scheduler page. |
| **EmptyState** | Custom | Icon + one sentence + primary action ("No companies yet — add your first"). Every list has one. |
| **Toast** | sonner | Success/failure of every mutation; errors include the API message. |
| **ConfirmDialog** | AlertDialog | Deletes and pause-alls only. |
| **Charts** | Recharts wrapped | Area (jobs over time), bars (per-company), line (success rate); consistent margins/axes; skeleton shimmer while loading. |

## 7. Interaction states

- **Loading:** skeletons for first load (cards/rows), inline spinners for refetch; optimistic updates for bookmark/applied toggles with rollback on error.
- **Focus:** visible 2px `--ring` outline, keyboard navigable throughout (Radix gives this largely free).
- **Motion:** 150ms ease-out for hover/expand; scan progress uses a subtle pulse on the status dot. No decorative animation.
- **Density toggle:** none in v1 — tables default comfortable-dense (40px rows).

## 8. Accessibility

- WCAG AA contrast on all text tokens (verified for both themes).
- All interactive elements ≥ 40px touch targets on mobile.
- Health/status never color-only: dot + word.
- Tables get `aria-sort`; toasts `aria-live=polite`; scan progress `role=status`.

## 9. Email design (constraint-driven)

- 600px single column, nested tables, all CSS inline; system font stack fallback (`-apple-system, Segoe UI, Roboto…`) since webfonts are unreliable in email.
- Dark-mode-safe colors (tested against Gmail/Apple Mail auto-invert); brand emerald header bar; one clear "Apply now →" button per job (44px tall, bulletproof-button pattern).
- Plaintext part mirrors the full content.
