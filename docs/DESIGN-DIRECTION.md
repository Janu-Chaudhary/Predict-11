# Predict-11 v2: UI/UX design direction ("Floodlight")

_Drafted 2026-10-02. Status: proposal for owner review. Scope: visual system, IA, wireframes, component
inventory, a11y, and do/don't. It builds on `docs/PLAN-v2.md` §3 (product features + UI principles)
and the scaffold in `web/` (Next.js 16, Tailwind 4, shadcn `base-nova`, Geist, lucide, `tokens.ts`).
No `web/` code was changed while writing this._

**One-line direction:** a FotMob/Sofascore-grade **data app** (dense, calm, tabbed, numbers first)
set at **night under floodlights**. The old site's identity (navy→indigo night stadium, gold CTA,
pink→violet brand gradient, team colours, pitch) survives as **atmosphere and accent**. It no longer
drives the layout.

---

## 0. Inputs reviewed

- **Old site** (`predict-your-11.netlify.app`, screenshots `/tmp/claude-1000/oldui/*.png`). Good:
  instant cricket/IPL mood, the gold CTA, team colours. Bad: marketing hero with no data, 60–90 px
  gradient headings taking most of the first screen, background gradient that stops at 900 px and
  leaves a white band (points table), a white light-theme card dropped on a dark page (H2H), three
  fonts (Poppins + Montserrat + Arial in buttons), emoji as icons, ~95 px table rows with
  centre-aligned numbers, filler stats ("LIVE · IPL · 10 Teams"), a dead-end empty state ("No live
  or upcoming matches available."), free-text inputs for player names, and a manual "Refresh
  Data" button.
- **Scaffold**: neutral shadcn tokens with a `--pitch` green, Geist/Geist Mono, `TEAMS` +
  `ROLE_THEME` in `src/lib/tokens.ts`, PitchView, RangeBar, PlayerCard, FreshnessBadge, side/bottom nav
  (Fixtures, Builder, Review, Accuracy).
- **Constraints from PLAN-v2 §6**: personal tool, **no live in-match data** (toss snapshot and
  post-match harvest about 1 h after the result), ranges rather than point estimates, freshness always
  visible, trust via the backtest page.

### Benchmarks and what we take from each

| Source | Pattern we adopt | Ref |
|---|---|---|
| FotMob | Minimal chrome so content dominates. Bottom tab bar with icon+label. Date strip with "Today" underline. Match page tabs. Lineup on a pitch. Player rating chips on the lineup. Coloured table zones. | [Pratt IxD critique](https://ixd.prattsi.org/2021/09/design-critique-fotmob-android-app/), [DesignRush](https://www.designrush.com/best-designs/apps/soccer-scores-pro-fotmob), [fotmob.us](https://fotmob.us/), [ratings def.](https://www.scribd.com/document/920258497/Stats-Definitions-FotMob) |
| Sofascore | **Attack Momentum**: a diverging bar strip showing who is on top, with incidents marked on it. Colour-banded player ratings. Win-probability graph. Heatmaps. | [Sofascore: Attack Momentum](https://www.sofascore.com/news/how-sofascores-attack-momentum-changed-sport-analysis), [Momentum & big chances](https://www.sofascore.com/news/understanding-football-match-stats-how-attack-momentum-and-big-chances-impact-performance), [Play Store](https://play.google.com/store/apps/details?id=com.sofascore.results&hl=en_US) |
| ESPNcricinfo | Worm, Manhattan, partnerships, wagon wheel, player-vs-player, Forecaster (win % + projected total). | [Stats Live IPL 2026 Q2](https://www.espncricinfo.com/series/ipl-2026-1510719/gujarat-titans-vs-rajasthan-royals-qualifier-2-1535464/statslive), [Wagon wheel help](http://static.espncricinfo.com/db/PRODUCTS/CRICVISION/help/wagon_wheel.html), [Superstats/Forecaster](https://www.espncricinfo.com/story/launching-superstats-the-new-language-for-cricket-analysis-1178276), [points table](https://www.espncricinfo.com/series/ipl-2025-1449924/points-table-standings) |
| Cricbuzz | Few top-level match tabs (Info / Live / Scorecard / Squads). A known pain point is too many tabs for the screen width. | [Cricbuzz scoreboard redesign case study](https://senguptamayukh.wordpress.com/2018/10/22/ux-ui-redesign-case-study-redesigning-a-live-cricket-scoreboard-on-cricbuzz/) |
| Chart vocab | Worm = cumulative runs + wicket dots. Manhattan = runs per over. Partnerships = stacked bar per pair. | [crickpro match charts](https://crickpro.com/cricket-league-website/match-pages/match-charts) |
| Dream11 | WK/BAT/AR/BOWL role tabs, a players-selected counter, live "credits left", sort by team/points/credits, an "i" for player info. | [ICC guide](https://www.icc-cricket.com/news/a-guide-to-icc-dream11-daily-fantasy-challenge), [Dream11 how to play](https://www.dream11.com/fantasy-cricket/how-to-play-fantasy) |
| 2026 trends | Bento grids **for overviews only** (they hurt uniform data scanning). Glass only on floating chrome. Variable fonts. Purposeful, accessible motion. | [rajeshrnair: what's actually shipping](https://rajeshrnair.com/blog/design/ui-ux/ui-design-trends-2026-bento-grids-glassmorphism.html), [Midrocket 2026](https://midrocket.com/en/guides/ui-design-trends-2026/), [Brucira](https://blog.brucira.com/top-ui-design-trends/), [gezar.dk](https://gezar.dk/en/blog/web-design-trends-2026) |

---

## 1. Design principles

1. **Numbers are the hero.** Each screen leads with the data the owner came for: next match, XI,
   projections, table. Headings are 16–24 px labels. They are not posters. No stock-photo
   marketing hero. The landing hero is itself made of real data (see §7.1).
2. **Floodlit, not flooded.** The night-stadium mood comes from a deep indigo base and one soft
   floodlight glow at the top of the shell. Gradients appear in the wordmark, the hero glow and the
   captain badge, and nowhere else. Cards, tables and charts are flat.
3. **Honest uncertainty.** A projection is shown as a range (floor–median–ceiling) or a probability
   with a confidence cue. We never print "guaranteed" and never show a lone 2-decimal number. After
   the match, the actual result is overlaid on the predicted range.
4. **Freshness is part of the content.** Every match surface shows its state: `Provisional`,
   `XI confirmed ✓ 19:02`, `Awaiting result`, `Reviewed`. The app refreshes itself, so there is no
   "refresh" button.
5. **One thumb, one sheet.** On mobile the primary actions sit in the bottom 40% of the screen.
   Player detail, lock/exclude and filters open in bottom sheets that keep context. A sticky bar
   shows the builder state (credits · roles · teams).
6. **Team colour is a signal, not a paint bucket.** Franchise colours mark identity: badge, 3 px
   stripe, and chart series in a match context. They are never full-card or page backgrounds and
   never body text.
7. **Same grammar everywhere.** A player row, range bar, form pills and team badge look the same
   in the builder, squad page, player profile and review, so the owner learns a screen once.
8. **Trust is one tap away.** Accuracy badges (e.g. "Captain top-2: 34% · 2026") link to the backtest
   page. The "Why this player" chips explain the model in plain words.

---

## 2. Visual system

### 2.1 Colour: neutrals ("Night" scale, hue about 275 indigo)

Dark is the default theme (`next-themes` `defaultTheme="dark"`; the toggle stays). Neutrals are
slightly tinted toward indigo so the app reads as "stadium at night" rather than grey. All values
are OKLCH to match `globals.css`.

| Token | Dark (default) | Light | Use |
|---|---|---|---|
| `--background` | `oklch(0.155 0.028 275)` ≈ #0B0E1C | `oklch(0.975 0.006 275)` ≈ #F5F6FA | page |
| `--surface-1` / `--card` | `oklch(0.195 0.032 275)` ≈ #131729 | `oklch(1 0 0)` | cards, table body |
| `--surface-2` / `--muted` | `oklch(0.235 0.036 275)` ≈ #1B2036 | `oklch(0.955 0.008 275)` | table header, hover, inset |
| `--surface-3` / `--popover` | `oklch(0.27 0.04 275)` | `oklch(1 0 0)` + shadow | menus, sheets |
| `--border` | `oklch(1 0 0 / 8%)` | `oklch(0.2 0.03 275 / 10%)` | hairlines |
| `--foreground` | `oklch(0.97 0.006 275)` | `oklch(0.2 0.035 275)` ≈ #151A30 | primary text |
| `--muted-foreground` | `oklch(0.72 0.025 275)` (≥ 4.5:1 on surface-1) | `oklch(0.48 0.03 275)` | secondary text |
| `--faint` | `oklch(0.58 0.025 275)` (labels ≥ 14 px only, ≥ 3:1) | `oklch(0.6 0.02 275)` | axis ticks, meta |

**Floodlight glow** (shell only): `radial-gradient(60% 320px at 50% -80px, oklch(0.55 0.16 285 / .35), transparent)`
on the dark `body::before`, fixed, behind the content. It replaces the old navy→purple
full-page gradient and has no seams.

### 2.2 Colour: accents and semantics

| Token | Dark | Light | Role |
|---|---|---|---|
| `--primary` (**Floodlight gold**) | `oklch(0.84 0.15 85)` ≈ #F4C542, text on it `#151A30` | fill `oklch(0.80 0.15 80)`; gold *text* uses `oklch(0.55 0.12 75)` | Primary CTA, selected state, C badge, focus ring. **At most one gold CTA per viewport.** |
| `--brand` (**Night violet**) | `oklch(0.68 0.19 295)` ≈ #9B7BF7 | `oklch(0.52 0.2 295)` | Links, active tab underline, info badges |
| `--brand-gradient` | `linear-gradient(90deg, #EC4899, #8B5CF6)` | same | **Only** the wordmark, the 2 px accent line under the Home hero, and the VC badge ring. This is the old site's heading gradient, shrunk to a signature. |
| `--pitch` | `oklch(0.42 0.09 150)` grass, `oklch(0.50 0.10 150)` stripe | `oklch(0.62 0.12 150)` | Pitch view field only |
| `--positive` | `oklch(0.78 0.16 155)` | `oklch(0.52 0.14 155)` | win, beat projection, +NRR |
| `--negative` | `oklch(0.70 0.19 25)` | `oklch(0.55 0.2 25)` | loss, wicket, below floor |
| `--warning` | `oklch(0.80 0.15 70)` | `oklch(0.6 0.14 65)` | provisional, conflict, doubtful |
| `--live` / `--info` | `oklch(0.75 0.13 230)` | `oklch(0.5 0.13 235)` | "XI confirmed", in-progress |

**Projection tier ramp** (a Sofascore-style rating chip for projected/actual fantasy points). It is
a single-hue violet→gold sequence so it never fights team colours, and the number is always printed:
`<20` surface-3 · `20–39` violet 35% · `40–59` violet · `60–79` gold 70% · `80+` gold.

**Ball outcome colours** (ball-by-ball, Manhattan markers): dot = faint ring, 1–3 = neutral chip,
4 = `--brand`, 6 = `--primary` gold, W = `--negative` with a "W" glyph, extras = `--warning` outline
with "wd/nb/lb".

### 2.3 Team colours (accents only)

`TEAMS` in `tokens.ts` keeps the brand `primary/secondary/onPrimary` for badges. Add a
**`chart` colour per team** tuned for legibility on the dark base (≥ 3:1 vs `--surface-1`), because
KKR purple, GT navy and MI navy disappear on night indigo:

| Team | badge (`primary`) | `chartDark` | `chartLight` |
|---|---|---|---|
| CSK | #F9CD05 | #F9CD05 | #B8920A |
| MI | #004BA0 | #4C8EF0 | #004BA0 |
| RCB | #C8102E | #EF4B5F | #C8102E |
| KKR | #3A225D | #A98BE0 | #3A225D |
| DC | #17449B | #6B95F2 | #17449B |
| PBKS | #D71920 | #FF7A6B | #D71920 |
| RR | #EA1A85 | #F25CA8 | #C2156E |
| SRH | #F26522 | #F7883F | #D4520F |
| GT | #1B2133 | #C9A86A (secondary gold) | #1B2133 |
| LSG | #0057E2 | #3FA0FF | #0057E2 |

Rules:
- Allowed: the circular `TeamBadge` (monogram or logo), a 3 px left stripe on match/player cards,
  the 2 px underline under the team name in the match hero, chart series, and the top border of the
  team page header.
- Not allowed: card or page fills, text colour, buttons, and table row backgrounds.
- **Clash rule:** in a two-team context (worm, momentum, H2H), compute the OKLab distance between
  the two `chart` colours. If ΔE < 0.12 (e.g. MI–DC–LSG blues, RCB–PBKS reds), the away team switches
  to its `secondary` (or `chartAlt`). If that still clashes, use neutral `--foreground` at 70%, and
  always add a shape cue (solid vs dashed line).
- Logos: store official crests locally as small SVG/PNG (personal tool) and render them at ≤ 40 px
  in badges. The monogram fallback is already in TeamBadge. Never use a crest as a card hero image.

### 2.4 Typography (Google Fonts, all variable)

| Role | Font | Settings | Why |
|---|---|---|---|
| UI / body / tables | **Geist** (already loaded) | 400/500/600; `font-feature-settings: "tnum","lnum"` on `.num` and all tables | Neutral, very legible at 12–14 px, variable, ships tabular figures |
| Display / scores / headings | **Saira** (variable `wght` 100–900, `wdth` 50–125) | headings `wdth 87.5, wght 650`; big scores `wdth 75, wght 700`, tabular | A condensed, scoreboard-like sports voice that replaces Poppins/Montserrat. One variable file covers both the broadcast numerals and the headings. |
| Codes / overs / IDs | **Geist Mono** (already loaded) | 500 | `14.3 ov`, ball codes, debug IDs |

Load Saira via `next/font/google` with `axes: ["wdth"]` as `--font-display`, and map `--font-heading`
to it in `@theme`. That makes 3 families in total, and nothing else is allowed.

**Scale** (rem at a 16 px root; mobile → desktop where different):

| Token | Size / line | Font | Use |
|---|---|---|---|
| `score-xl` | 40/44 → 48/52 | Saira 700 w75 tnum | Match hero score, projected team total |
| `display` | 28/32 → 32/36 | Saira 650 w87 | Page titles (only one per page) |
| `title` | 20/26 → 22/28 | Saira 600 w87 | Section titles in cards |
| `heading` | 16/22 | Geist 600 | Card headings, sheet titles |
| `body` | 14/20 | Geist 400 | Default (dense app) |
| `body-lg` | 16/24 | Geist 400 | Long text: preview, explanations |
| `table` | 13/18 → 14/20 | Geist 400/500 tnum | Scorecards, tables |
| `caption` | 12/16 | Geist 500 | Meta, legends |
| `overline` | 11/14, +0.06em, uppercase | Geist 600 | Column headers, labels. **11 px is the floor.** |

Numbers in tables are right-aligned and tabular. Names are left-aligned. A row's primary stat uses weight
600, not colour.

### 2.5 Spacing, radius, elevation, layout

- **Grid:** 4 px base. Steps are 4, 8, 12, 16, 20, 24, 32, 48. Card padding is 12 (mobile) / 16 (desktop).
  Gaps between cards are 12 / 16. Section gaps are 24 / 32.
- **Density:** list rows are 52 px (touch). Desktop table rows are 36 px, and 44 px with an avatar.
  A "Compact" toggle on tables drops rows to 32 px.
- **Radius:** `--radius: 0.75rem`. Cards 12. Inner tiles 8. Buttons and inputs 10. Chips and badges full.
  Bottom sheets 20 on the top corners. The pitch view is 16.
- **Elevation in dark mode = lightness steps** (background → surface-1 → 2 → 3) plus a 1 px border.
  Shadows only exist in light mode (`0 1px 2px / 6%`, `0 8px 24px / 10%` for overlays).
- **Glass (sparingly):** `bg-surface-1/72 backdrop-blur-xl border-white/8`, only for the sticky top
  bar, bottom nav, sticky builder bar and bottom sheets. No glass on cards. Provide a solid fallback when
  `prefers-reduced-transparency` is set.
- **Layout:** mobile single column with 16 px gutters. Tablet ≥ 768 adds 2-column tiles. Desktop
  ≥ 1024 adds a left rail and a 12-column content area capped at 1280 px. Match centre desktop puts tab
  content in an 8-column main area with a 4-column sticky right rail ("Fantasy snapshot").
- **Bento:** Home and match Summary only (overview tiles of mixed size). Tables, scorecards and
  lists use uniform rows (per the trend research cited above).

### 2.6 Iconography

- **lucide** (already configured): 20 px, stroke 1.75, `currentColor`. No emoji anywhere.
- A small **custom cricket set** in the same stroke style (SVG components in `components/icons/`):
  bat, ball, stumps (wicket), gloves (WK), all-rounder (bat+ball), helmet (impact player), coin
  (toss), dew drop, pitch strip, captain "C" and vice "VC" roundels.
- Role chips show both an icon and a text code (`WK` `BAT` `AR` `BOWL`) and keep the existing
  `ROLE_THEME` hues (amber/sky/violet/emerald). These four hues are reserved for roles.

### 2.7 Charts

General rules: Recharts via the shadcn `chart` wrapper (custom SVG for the wagon wheel and pitch). Hairline
grid at `--border` and horizontal lines only. Axis ticks are 11–12 px `--faint` and tabular. Label the
series directly instead of using legends where possible. No 3D, no gradient bars, no drop shadows. Every
chart has a **"Table" toggle** and an `aria-label` summary. Tooltips are surface-3 cards with
tabular numbers. Team series use the `chartDark/Light` colour plus a shape/dash difference.

| Chart | Spec |
|---|---|
| **Worm** | X = overs 0–20, Y = cumulative runs. Two lines (2 px, team chart colours, away team dashed if clashing). Wickets are 6 px dots with a surface ring. Powerplay (0–6) is a shaded band at 4%, with a death-overs (16–20) band. The tooltip shows `14.3 · 128/4 · RR 8.8`. |
| **Manhattan** | Bars per over, grouped by innings (desktop) or an innings toggle (mobile). Bar = team colour at 85%. Wickets are dots stacked above the bar. The par-RR line is a dashed `--faint` line. |
| **Over momentum** (Sofascore analogue) | A diverging strip of 20 bars. Above the axis is team A's (runs − par) per over, below it is team B's. Wicket and milestone glyphs sit on the strip. This is the hero chart of the Summary tab. |
| **Win probability** | Pre-match model % plus a post-match reconstruction per over. Area around a 50% midline: above = team A colour at 25% fill, below = team B. The end label shows the final %. Never shown "live". |
| **Wagon wheel** | SVG oval field (pitch green at 20%) with 30-yard circle hairlines. Rays from the striker's end: 1–3 neutral at 50%, 4 violet, 6 gold. With no shot coordinates, it falls back to **8 zone sectors** shaded by runs (from the commentary "to deep midwicket" text). The source is labelled. |
| **Partnerships** | One horizontal row per wicket: batter 1 left and batter 2 right of the centre, coloured by role, with runs (balls) at each end. |
| **Range bar** (exists) | Track = surface-3. Band floor→ceiling = tier colour at 35%. Median = 2 px solid tick + number. Post-match actual = diamond marker (positive/negative colour if outside the band). |
| **Form** | The last 5–10 fantasy scores as **mini bars** (not lines), tier-coloured, with the newest on the right. Team form = W/L/NR pills with a letter + colour. |
| **Exposure heatmap** | Players × lineups. Cell = surface steps → gold. Values are printed on hover/focus. |
| **Calibration** (Accuracy) | Predicted vs actual quantile coverage against a diagonal reference. Points sized by n. |

### 2.8 Motion

- Durations: **120 ms** micro (press, toggle), **200 ms** standard (tab underline, chip), **320 ms**
  sheets/dialogs. Charts draw once **≤ 600 ms** on first reveal and do not redraw on tab revisit.
- Easing: `cubic-bezier(0.2, 0, 0, 1)` (emphasised decelerate) to enter, `cubic-bezier(0.4, 0, 1, 1)`
  to exit.
- **Purposeful motion only:**
  - Re-optimize diff: swapped-in players get a gold ring pulse (600 ms, once) and a `+` chip, and
    swapped-out players fade with a `−` chip on the bench list.
  - Number tick: the credits bar, projected total and table points count to the new value in 300 ms.
  - Freshness badge: a single shimmer when the state flips to "XI confirmed".
  - Shared-element/View Transition from a match card to the match hero, where supported.
- `prefers-reduced-motion`: everything becomes a 120 ms opacity fade, with no pulses, counts or chart draw-in.
- No parallax, no auto-carousels, no decorative looping animations (loaders in §7.2 are the only
  loops), and no glow text-shadows.
- Landing hero, loaders, route transitions and optimistic UI are specified in §7.

---

## 3. Information architecture and navigation

### 3.1 Routes

```
/                         Home: today/next match hero, my XI status, table snippet, accuracy badge
/matches                  Fixtures & results (date strip, team filter, season switch)
/matches/[id]             Match centre, tabs as ?tab= (shareable, back-button friendly):
   summary | scorecard | balls | lineups | fantasy | stats | h2h | review
/builder/[matchId]        Fantasy builder (pitch ⇄ list), portfolio, rate-my-team
/table                    Points table + qualification scenarios + projected finish
/teams, /teams/[code]     Team index → team page (Squad | Fixtures | Stats | Venues)
/players/[id]             Player profile (Overview | Fantasy | Batting | Bowling | Matchups | Log)
/h2h                      Head-to-head: Team vs Team | Batter vs Bowler | Player vs Team
/accuracy                 Backtest & calibration (the trust page)
/settings                 Theme, compact tables, credits entry, data sources/admin conflicts
```

Global **search** (players, teams, venues, matches) opens with ⌘K on desktop and the top-bar
search icon on mobile, using the shadcn Command component. It replaces every free-text name box.

### 3.2 Navigation

- **Mobile bottom nav (5, glass, 64 px + safe area):** `Home` · `Matches` · **`Build`** (centre,
  gold icon when a match is open for building) · `Table` · `More` (Teams, Players, H2H, Accuracy,
  Settings in a sheet).
- **Desktop left rail:** 72 px icon+label rail, expandable to 240 px. Primary links (Home, Matches,
  Build, Table) and Explore links (Teams, Players, H2H, Accuracy) are separated by a divider, with
  Settings at the bottom.
- **Top bar** (all sizes, glass, 56 px): wordmark (gradient) · global freshness pill ("Data 19:02") ·
  search · theme toggle. On match pages it collapses to a compact score header on scroll.
- **Match tabs:** a horizontally scrollable `Tabs` list with a sticky top under the compact header.
  Mobile shows the first 4–5 tabs plus edge fade, and the active tab auto-scrolls into view.
- The scaffold's `Fixtures/Builder/Review/Accuracy` nav maps as follows: Fixtures → Matches, Review →
  match tab `review`.

### 3.3 Match state drives tabs (no live data)

| State | Badge | Default tab | Tabs available |
|---|---|---|---|
| Upcoming (> T-35 min) | `Provisional` (warning) | Fantasy | Summary (preview, conditions), Lineups (probable XI with P(plays)), Fantasy, Stats (season), H2H |
| XI confirmed | `XI confirmed ✓ 19:02` (info) | Fantasy | + Lineups (confirmed + impact subs) |
| In progress | `In progress · review ~1 h after result` | Summary | Same as above. Scorecard shows an empty state with ETA (no live). |
| Completed, harvesting | `Result in · harvesting` | Scorecard | + Scorecard, Balls (as available) |
| Reviewed | `Reviewed ✓` | Review | All, including Stats charts and Review |

Each tab that has no data yet shows *why* and *when* (e.g. "Ball-by-ball arrives ~45 min after the
result; last attempt 22:41, next 23:41"). There are no dead-end empty states.

---

## 4. Wireframes (ASCII)

Legend: `▌` team stripe, `[ ]` button, `( )` chip, `▓▒░` range bar, `═` sticky element.

### 4.1 Home

The visual behind or beside the match card is the **landing hero from §7.1** (recommended: the
Wagon-Wheel Bloom; prototype `docs/design/hero-wagon-wheel.html`). The wireframes below show the
data layer that sits on top of it.

Mobile (390):
```
┌──────────────────────────────────────┐
│ ◆Predict-11      (Data 19:02 ✓)  ⌕ ◐ │ ═ top bar (glass)
├──────────────────────────────────────┤
│ TODAY · Match 41 · Chepauk · 19:30   │  ← overline
│ ┌──────────────────────────────────┐ │
│ │ (CSK)  CSK        vs     MI  (MI)│ │  floodlight glow behind
│ │ ▔▔▔▔▔ yellow          ▔▔▔ blue  │ │
│ │ Win prob  CSK 56% ███████░░░ 44% │ │
│ │ (XI confirmed ✓ 19:02) Toss: MI ▸bowl│
│ │ [   Build my XI  →   ] (gold)    │ │  one gold CTA
│ └──────────────────────────────────┘ │
│ ┌─────────────┐ ┌──────────────────┐ │  bento (2-up)
│ │Best XI proj │ │ Captain picks    │ │
│ │ 612 pts     │ │ C  Gaikwad 31%   │ │
│ │ ▓▓▒▒░ 480–740│ │ VC Bumrah  22%  │ │
│ └─────────────┘ └──────────────────┘ │
│ ┌──────────────────────────────────┐ │
│ │ Conditions: par 182 · dew high · │ │
│ │ spin 58% · chase won 7/10        │ │
│ └──────────────────────────────────┘ │
│ UP NEXT                          All ›│
│ ▌RCB v KKR   Sat 15:30   Provisional │
│ ▌GT  v RR    Sat 19:30   Provisional │
│ TABLE (top 4)                  Full ›│
│ 1 ▌PBKS 9 3 18 +0.41  WWLWW          │
│ ...                                  │
│ (Model: captain top-2 34% · 2026 ›)  │  trust badge → /accuracy
├══════════════════════════════════════┤
│ ⌂Home  ▦Matches  ◉Build  ≡Table  ⋯More│ ═ bottom nav
└──────────────────────────────────────┘
```
Desktop (1440):
```
┌rail┬──────────────────────────────────────────────────────────────────────┐
│ ⌂  │ ◆Predict-11                    (Data 19:02 ✓)   [⌕ Search  ⌘K]   ◐   │
│ ▦  ├───────────────────────────────────────────────┬──────────────────────┤
│ ◉  │ MATCH HERO (8 col)                            │ TODAY'S PICKS (4 col)│
│ ≡  │ (CSK) CSK  vs  MI (MI)  Chepauk 19:30         │ C  Gaikwad  ▓▓▒░ 58  │
│ ── │ Win prob bar · toss · (XI confirmed ✓)        │ VC Bumrah   ▓▒░  49  │
│ ⚑  │ [Build my XI →]  [Match centre]               │ Differential: Shivam │
│ 👤 │                                               │ [Open builder]       │
│ ⇄  ├──────────────┬───────────────┬────────────────┼──────────────────────┤
│ ✓  │ Best XI proj │ Conditions    │ Over-momentum  │ POINTS TABLE (top 6) │
│    │ 612 ▓▒░      │ par/dew/spin  │ last meeting   │ + form pills         │
│ ⚙  ├──────────────┴───────────────┴────────────────┤                      │
│    │ FIXTURES · date strip  Thu Fri [Sat] Sun      │ ACCURACY 2026        │
│    │ ▌RCB v KKR 15:30 Provisional   ▌GT v RR 19:30 │ cap top-2 34% · MAE  │
└────┴───────────────────────────────────────────────┴──────────────────────┘
```

### 4.2 Match centre: Summary tab

Mobile:
```
┌──────────────────────────────────────┐
│ ‹  CSK v MI · M41 · Chepauk     ⋯    │
│ (CSK) 186/5 (20)    MI 172/8 (20)(MI)│  score-xl (Saira, tabular)
│ CSK won by 14 runs · POTM Gaikwad    │
│ (Reviewed ✓ 23:10)                   │
│ Summary Scorecard Balls Lineups Fan››│ ═ sticky scroll tabs
├──────────────────────────────────────┤
│ OVER MOMENTUM                        │
│  CSK ▁▃▅▂▁▆▇▃▂▁▂▄▅▃▁▂▆▇▅▃            │  diverging bars, W glyphs
│  ─────────────────────────────── 0   │
│  MI  ▂▁▃▅▂▁▁▃▄▂▁▂▃▅▂▁▃▂▅▆            │
│  PP │      middle       │ death       │
├──────────────────────────────────────┤
│ WIN PROBABILITY  (pre-match 56%)  ▸  │
│ ~~~~~~~~~~~~~~~~~~~~~~ 50% midline   │
├──────────────────────────────────────┤
│ TOP PERFORMERS (fantasy pts)         │
│ (BAT) Gaikwad CSK  92  (pred 48 ▓▒░◆)│  actual diamond on range
│ (BOWL) Bumrah MI   71  (pred 52 ▓▒◆░)│
├──────────────────────────────────────┤
│ KEY MOMENTS  14.3 W Rohit c Jadeja … │
│ CONDITIONS  par 182 · dew yes · toss │
│ PREVIEW (LLM, 150 words, from data)  │
└──────────────────────────────────────┘
```
Desktop: score header across 12 columns. Tabs below it. The main 8 columns hold Over Momentum (full width),
then a 2-up of Win prob and Worm thumbnail (→ Stats), then a Top performers table. The 4-column right rail is
sticky: Fantasy snapshot (best XI total, C/VC, my XI rank once reviewed), Conditions, Data sources
(`Cricsheet ✓ · Cricinfo ✓ · Cricbuzz ⚠ conflict`).

### 4.3 Fantasy tab and Builder (pitch view + list)

Mobile, pitch view (default):
```
┌──────────────────────────────────────┐
│ ‹ Build · CSK v MI    (XI conf ✓)  ⋯ │
│ [Pitch | List]   Risk: Safe ●──○── Contrarian │  one risk control
│ ┌──────────────── pitch ───────────┐ │
│ │ WK      (Dhoni 6.5)              │ │  player tokens:
│ │ BAT (Gaikwad C)(Rohit)(SKY)      │ │  badge, name, proj median,
│ │ AR  (Jadeja)(Hardik VC)(Dube)    │ │  team stripe, C/VC roundel,
│ │ BOWL(Bumrah)(Pathirana)(Chahar)🔒│ │  lock icon
│ └──────────────────────────────────┘ │
│ Why: (Opens at Chepauk)(vs spin ↑)   │  SHAP chips for selected
│ Changes: +Dube −Tilak (+6.2 pts) ✕   │  diff toast after re-opt
├══════════════════════════════════════┤
│ 11/11 · 98.5/100 cr · CSK 6 MI 5 · ✓ │ ═ sticky builder bar
│ Proj 612 ▓▓▒▒░ 480–740  [Save] [⋯]   │
└──────────────────────────────────────┘
 tap player → bottom sheet:
 ┌──────────────────────────────────────┐
 │ (CSK) R Gaikwad  BAT · 9.0 cr · 31% own│
 │ ▓▓▓▒▒░░  floor 18 · med 48 · ceil 96 │
 │ Form ▂▅▃▇▄  Venue avg 54 (n=9)       │
 │ [Lock] [Exclude] [Make C] [Make VC]  │
 │ View profile ›                       │
 └──────────────────────────────────────┘
```
Mobile, list view: role tabs `WK(1) BAT(4) AR(3) BOWL(3)` with live counts, sort `Proj ▾ · Credits ·
Own% · Value`, filter by team chips. Each row is
`▌badge  Name  role  cr  ▓▒░ median  [+]`. Selected rows show a check, and locked/excluded rows show icons.

Desktop:
```
┌rail┬───────────────────────────────────────────────┬─────────────────────────┐
│    │ CSK v MI · Build   (XI confirmed ✓ 19:02)     │ POOL (list, 22+subs)    │
│    │ Risk ●──○──  [Lineups: 1 ▾] [What-if: toss/dew]│ [WK][BAT][AR][BOWL]     │
│    │ ┌──────────── pitch view ─────────────┐       │ sort Proj ▾  CSK MI     │
│    │ │   rows of 11 tokens                  │       │ ▌Gaikwad BAT 9.0 ▓▒░ 48+│
│    │ └──────────────────────────────────────┘       │ ▌Rohit   BAT 9.5 ▓▒░ 44+│
│    │ CAPTAIN PICKS  C/VC table w/ ranges, top-2 %  │ ...                     │
│    │ PORTFOLIO (N lineups) · exposure heatmap      │ player detail drawer    │
│    ├═══════════════════════════════════════════════┴═════════════════════════┤
│    │ 11/11 · 98.5 cr · CSK 6 / MI 5 · roles ✓ · Proj 612 (480–740) [Save] [Rate my team] │
└────┴─────────────────────────────────────────────────────────────────────────┘
```
The **Fantasy tab** in the match centre is the read-only version: Best XI (pitch), Captain picks
table, "Projections" table for all 22+ players (range bars, own%, value), a Differentials list, and
`[Open in builder →]`.

### 4.4 Squad page (`/teams/[code]`)

Mobile:
```
┌──────────────────────────────────────┐
│ ‹ (CSK) Chennai Super Kings          │  2 px yellow top border only
│ P 9 · W 6 · L 3 · 3rd · form WWLWW   │
│ Squad  Fixtures  Stats  Venues       │ ═ tabs
├──────────────────────────────────────┤
│ [All][WK][BAT][AR][BOWL]  sort Proj ▾│
│ WICKET-KEEPERS (2)                   │
│ ◯ MS Dhoni  WK · 6.5cr  ▂▃▂▅▄  ▓▒░ 31│
│ BATTERS (6)                          │
│ ◯ R Gaikwad (C) 9.0cr ▅▇▄▆▅ ▓▓▒░ 48  │
│ ◯ D Conway (overseas ✈) ...          │
│ (Injured ✚) (Replacement for X)      │  status chips
└──────────────────────────────────────┘
```
Desktop: header band (badge, record, form, next fixture) and a sortable `Table` with columns: Player ·
Role · Credits · Matches · Avg pts · Form (bars) · Proj range · Own% · Status. A 4-column right rail holds
"Likely XI" (mini pitch with P(plays) %) and "Impact-sub tendency".

### 4.5 Player profile (`/players/[id]`)

Mobile:
```
┌──────────────────────────────────────┐
│ ‹  ◯ Ruturaj Gaikwad   (CSK)         │
│ BAT · RHB · Opener · 9.0 cr          │
│ ┌────────┐┌────────┐┌────────┐       │  stat tiles (tabular)
│ │Avg pts ││ Ceil p90││ C-rate │       │
│ │  48.2  ││   96    ││  18%   │       │
│ └────────┘└────────┘└────────┘       │
│ Overview Fantasy Batting Bowling Mat›│ ═ tabs
├──────────────────────────────────────┤
│ NEXT: vs MI @Chepauk  ▓▓▒▒░ 18–48–96 │
│ Why: (Opens at Chepauk)(vs pace avg 41)│
│ FORM (last 10)  ▂▅▃▇▄▅▆▃▂▇ (tier bars)│
│ SPLITS  Venue · vs pace/spin · bat 1st/chase (bars)│
│ MATCHUPS  vs Bumrah 34(28) 2 outs ⚠ low n │
│ MATCH LOG  date opp runs balls pts pred│
└──────────────────────────────────────┘
```
Desktop: a header across the full width. The left 8 columns hold the tabs, and the right 4 columns are
sticky ("Next match projection" card + "Add to XI" when a builder session is open).

### 4.6 Head-to-head (`/h2h`)

Mobile:
```
┌──────────────────────────────────────┐
│ Head-to-head                         │
│ [Teams | Batter v Bowler | Player v Team]│ segmented
│ (CSK ▾)        vs        (MI ▾)      │  searchable pickers (Command)
├──────────────────────────────────────┤
│ ALL-TIME  CSK 17 ███████░░░░░ 20 MI  │  split bar, team colours
│ Last 5:  W L W W L                   │
│ At Chepauk: CSK 6–3                  │
│ AVG 1st-INNS  178 vs 171             │  mirrored stat rows
│ TOP FANTASY SCORERS IN FIXTURE       │
│ MATCH LIST  date venue result ›      │
└──────────────────────────────────────┘
 Batter v Bowler mode:
│ (Kohli ▾)  vs  (Bumrah ▾)            │
│ Balls 64 · Runs 71 · Outs 3 · SR 111 │
│ Dot% 41  4s 7  6s 2   (n=64 · medium confidence)│
│ Ball outcome strip ● ● 4 ● 1 W 6 ...  │
│ vs bowler TYPE (fallback when n<30):  │
│   vs right-arm fast  SR 138 (n=812)  │
```
Desktop: the pickers sit in a top band. Below is a 2-column mirrored layout (team A stats left-aligned,
team B right-aligned, metric labels centred) like FotMob's stat comparison, then a matches table.

### 4.7 Points table (`/table`)

Mobile:
```
┌──────────────────────────────────────┐
│ Points table · IPL 2026   (Data 23:10)│
│ [Table | Scenarios | Projected]       │
├──────────────────────────────────────┤
│ #  Team   P  W  L  NR  NRR   Pts Form│  sticky header
│ ▌1 (PBKS) 9  6  2  1  +0.41  13 WWLWW│  ▌ = zone stripe:
│ ▌2 (RCB)  9  6  3  0  +0.30  12 WLWWW│  gold = top 2 (Q1)
│ ▌3 (CSK)  9  5  3  1  +0.25  11 LWWWL│  violet = 3–4 (Elim.)
│ ▌4 (MI)   9  5  4  0  +1.14  10 WWLLW│
│  5 (DC)   ...                         │
│ ── qualification line ─────────────── │
│ Zone key: ▌Qualifier 1  ▌Eliminator   │
└──────────────────────────────────────┘
 Scenarios tab:
│ CSK · 5 left · qualify 71% ▓▓▓▓▓▓▓░░ │
│ • Win 3 of 5 → 94% (NRR irrelevant)  │
│ • Win 2 of 5 → 38% (needs NRR > MI)  │
│ Must-watch: M44 RCB v MI (swings 12%)│
```
Desktop: the full table on the left 8 columns, with an extra "Qualify %" column (range bar) and "Next" (badge of the
next opponent). The right 4 columns show the selected team's scenario card plus a "Projected finish" distribution
(position probability heat row per team, from simulation).

---

## 5. Component inventory

### 5.1 shadcn primitives to add (`pnpm dlx shadcn@latest add …`, base-nova on Base UI)

`tabs`, `sheet` (side + bottom), `drawer` (mobile bottom sheets), `dialog`, `command` (global search +
pickers), `popover`, `dropdown-menu`, `select`, `toggle-group` (Pitch/List, segmented modes),
`slider` (risk), `switch` (what-if), `table` (+ TanStack Table for sort/sticky), `scroll-area`,
`separator`, `avatar`, `progress`, `chart` (Recharts), `sonner` (re-opt/save toasts), `hover-card`,
`collapsible`/`accordion` (advanced knobs), `input`, `label`, `kbd`, `breadcrumb` (desktop),
`sidebar` (desktop rail). Already present: `button`, `badge`, `card`, `skeleton`, `tooltip`.

### 5.2 Product components

| Area | Components |
|---|---|
| Shell | `TopBar`, `SideRail`, `BottomNav`, `FreshnessBadge`*, `MatchStateBadge`, `GlobalSearch`, `ThemeToggle`*, `EmptyState`* (with "why + when"), `ErrorState`, `PageHeader`* |
| Identity | `TeamBadge`* (+ crest), `TeamStripe`, `RoleChip`* (+ icon), `CaptainRoundel` (C gold / VC gradient ring), `StatusChip` (injured, overseas, impact, doubtful) |
| Match | `MatchCard` (list row), `MatchHero`, `ScoreHeader` (collapsing), `DateStrip`, `ConditionsCard`, `KeyMoments`, `SourceStatus` (merge/conflict) |
| Scorecard | `BattingTable`, `BowlingTable`, `FallOfWickets`, `ExtrasRow`, `ImpactSubRow`, `OverRow` + `BallChip` (ball-by-ball) |
| Charts | `OverMomentum`, `WinProbChart`, `WormChart`, `ManhattanChart`, `WagonWheel`, `PartnershipBars`, `FormBars`, `RangeBar`*, `SplitBar` (H2H), `ExposureHeatmap`, `CalibrationChart`, `PositionHeatRow`, `ChartTableToggle` |
| Player | `PlayerRow`, `PlayerCard`*, `PlayerSheet` (bottom sheet / drawer), `StatTile`, `WhyChips` (SHAP), `MatchupTable`, `SplitBars` |
| Builder | `PitchView`* (tokens, C/VC, lock), `PlayerToken`, `PoolList` (role tabs + sort + team filter), `BuilderBar` (sticky credits/roles/teams/proj), `RiskSlider`, `WhatIfPanel`, `DiffChip` + diff toast, `CaptainPicksTable`, `PortfolioGrid`, `RateMyTeam` |
| Table | `PointsTable` (zones, form pills, sticky header), `FormPills`, `ScenarioCard`, `QualifyBar` |
| Trust | `AccuracyBadge` (links to /accuracy), `BacktestTable`, `SeasonSwitcher` |

`*` = exists in the scaffold and gets restyled to the new tokens.

### 5.3 Accessibility rules (WCAG 2.2 AA minimum)

1. **Contrast:** text ≥ 4.5:1 (≥ 3:1 for ≥ 18.66 px bold). Chart marks, borders that carry meaning, and focus
   rings ≥ 3:1 against adjacent colours. Validate both themes in CI (e.g. a token contrast unit test).
2. **Colour is never the only signal:** W/L/NR pills carry letters. Wickets are glyphs. Team series
   differ by dash/shape. Above/below range uses ▲/▼ plus colour. Zones in the table have a key + `aria-describedby`.
3. **Targets:** ≥ 44×44 px for primary touch controls (pitch tokens, nav, chips). ≥ 24 px absolute
   minimum (WCAG 2.5.8) for dense desktop table icons, with spacing.
4. **Keyboard:** everything reachable. Tabs use roving focus (Base UI). The pitch view is a grid with
   arrow-key navigation, and `Enter` opens the sheet. ⌘K for search. `Esc` closes sheets and returns focus.
   Visible 2 px gold focus ring with 2 px offset.
5. **Screen readers:** each chart has an `aria-label` summary ("CSK led momentum in overs 6–9 and
   16–19") and a table alternative. Re-optimize results are announced through `aria-live="polite"`
   ("XI updated: 2 changes, projected 612"). Range bars are labelled "projected 48, range 18 to 96". Sort
   headers carry `aria-sort`.
6. **Text:** 11 px floor. Works at 200% zoom and 320 px width without horizontal page scroll (tables
   scroll inside their own region with a sticky first column). `lang="en"`.
7. **Motion and transparency:** honour `prefers-reduced-motion` and `prefers-reduced-transparency`
   (solid fallback for glass).
8. **Landmarks:** one `<h1>` per page. `nav`, `main#main` (the skip link exists), `aside` for rails.

---

## 6. Do / Don't (fixing the old site)

| Don't (old site) | Do (v2) |
|---|---|
| Full-screen stadium photo hero with "IPL FANTASY TEAM PREDICTOR" and a CTA, but no data | Open on the next match's data: teams, time, state, win %, best-XI range, one gold CTA |
| 60–90 px pink→purple gradient headings on every page | Saira 28–32 px solid headings. The gradient lives only in the wordmark and the VC ring. |
| A page gradient that ends mid-scroll and leaves a white band | Solid `--background` + fixed floodlight glow on `body`, with no seams at any height |
| A white light-theme card inside a dark page (H2H) | One theme per render. Every surface comes from tokens. |
| Poppins + Montserrat + Arial mixed | Geist + Saira + Geist Mono, defined once in `layout.tsx` |
| Emoji icons (🏏 🎯) | lucide + a custom cricket glyph set at the same stroke weight |
| Boxed two-line nav buttons across the top | Bottom nav (mobile) and left rail (desktop) with icon + one-word label |
| 95 px table rows, centred numbers, 60 px crest images in rows | 36–52 px rows, right-aligned tabular numbers, 24–28 px badges |
| Team crests as full card backgrounds (squads grid) | Badge + 3 px stripe. Team colour is an accent, never a fill. |
| Filler stats ("LIVE · IPL · 10 Teams") | Every number on screen is real data or it is removed |
| "No live or upcoming matches available." dead end | Empty states say why, when data arrives, and link to the nearest useful screen |
| Manual "Refresh Data" button + "Last updated 12:55:51 AM" | Automatic refetch (TanStack Query) + `FreshnessBadge` with state and relative time |
| Free-text batter/bowler name inputs | Command-palette pickers backed by the player registry (IDs, not names) |
| Pink used for rank, points and headings alike | Emphasis by weight. Colour is reserved for meaning (positive/negative/tier/team). |
| Single numbers like "Total credits 82.5" in big pink | Sticky builder bar: `11/11 · 98.5/100 cr · CSK 6 MI 5 · roles ✓` |
| Glowing text-shadows | No text-shadow. Depth comes from surface steps. |
| Separate pages per feature with no links between them | Same `PlayerRow`/`TeamBadge` everywhere, all tappable through to profile/match/team |

Also:
- **Do** keep at most one gold primary button per viewport, and **don't** colour secondary actions.
- **Do** show ranges and n-sizes. **Don't** show ML internals or 2-decimal projections on the surface.
- **Do** test every screen at 360 px wide and in light mode before merging. **Don't** ship dark-only.
- **Do** render skeletons that match the final layout. **Don't** use spinners over blank pages.
- **Don't** use bento layouts for tables, scorecards or lists.

---

## 7. Landing hero and loading system

The old home page was a stock night-stadium photo with a slogan. v2 replaces it with a hero that is
**generated from our own data**, so it is different every match day and doubles as information.
Every concept below sits *behind or beside* the next-match card (teams, countdown, win %, state, one
gold CTA). The card is identical across concepts, so the choice only affects the visual layer.

### 7.1 Three hero concepts

#### Concept A: "Wagon-Wheel Bloom" (recommended)

The last completed match's best innings (or the next match's top projected batter's career wheel
at this venue) is drawn as scoring rays that bloom out from the striker's end across a stylised oval:
singles faint, fours violet, sixes gold, with a dot on the boundary rope.

```
 Desktop                                         Mobile
┌──────────────────────────┬─────────────────┐  ┌──────────────────────┐
│        .  ╱  ╲  .        │ NEXT MATCH · M42 │  │   (wheel, 280 px,    │
│     ·  ╱   ··   ╲ ·  ●   │ (CSK) CSK v MI(MI)│  │    40% opacity,      │
│   ●───────(▮)────────●   │ ┌──┐┌──┐┌──┐     │  │    behind the card)  │
│     · ╲  ·   ·  ╱ ·      │ │03││14││04│     │  │ ┌──────────────────┐ │
│      ●  ╲    ╱   ●       │ └──┘└──┘└──┘     │  │ │ NEXT · CSK v MI  │ │
│   Last match · Gaikwad 92│ CSK 56% ████░ 44%│  │ │ 03:14:04  56/44  │ │
│   ─1–3 ─4 ─6              │ [Build my XI →]  │  │ │ [Build my XI →]  │ │
└──────────────────────────┴─────────────────┘  └──┴──────────────────┴─┘
```

- **Motion:** the rays draw in ball order with `stroke-dashoffset` (≈45 ms stagger, 360 ms per single and 520 ms per
  boundary, ≈2.6 s total). Boundary dots fade in as each ray lands. The countdown digits flip
  (320 ms). The win-probability bar fills once (900 ms). After that, everything is still. There is
  no idle loop. Hovering or focusing a ray shows `14.3 · Bumrah → deep midwicket · 6`.
- **Tech:** inline **SVG + Web Animations API**. 0 KB of libraries, server-renderable paths (Next RSC
  computes the geometry, and the client only animates). If the codebase adopts **Motion**
  (`motion/react`, about 5 KB gz for the `animate` mini build and about 15 KB for `LazyMotion` +
  `domAnimation`), use `pathLength` animation. GSAP is not needed.
- **Data:** commentary gives a field region rather than an angle ("to deep midwicket"). Map each of
  the ~16 standard field-position names to an angle band, jitter inside the band, and set length by runs.
  If ball-by-ball is missing, fall back to the **8-sector** wheel (filled wedges).
- **Performance:** ≤ 200 paths, no filters/blur on paths, `will-change` not needed. LCP is the match
  card text, not the SVG. Runs fine on low-end Android.
- **Reduced motion:** render the finished wheel statically, with no countdown flip (numbers just
  update) and the bar at its final width.
- **Why it wins:** it is uniquely *cricket* (football apps cannot do this), it uses real data, it is the
  cheapest concept, it reuses the `WagonWheel` chart component from §2.7, and it looks good in both
  themes. **Prototype:** `docs/design/hero-wagon-wheel.html` (synthetic data, theme toggle,
  reduced-motion aware).

#### Concept B: "XI Assembles"

The predicted best XI builds itself. 22 player tokens start as two loose "benches" in team colours
on the left and right. The model's 11 picks fly into WK/BAT/AR/BOWL rows on a pitch, credits tick up in
the builder bar, and the C (gold) and VC (gradient ring) roundels pop on last. It ends as a
static mini-pitch whose CTA reads "Tweak this XI →".

```
┌───────────────────────────────────────────────┐
│ (CSK bench)  ┌──────── pitch ────────┐  (MI)  │
│  ○ ○ ○  →→→  │ WK      (●)           │ ←←← ○ ○│
│  ○ ○ ○       │ BAT (●C)(●)(●)        │     ○ ○│
│  ○ ○         │ AR  (●)(●VC)(●)       │     ○  │
│              │ BOWL(●)(●)(●)         │        │
│              └───────────────────────┘        │
│  11/11 · 98.5 cr · Proj 612 (480–740)  [Tweak]│
└───────────────────────────────────────────────┘
```

- **Motion:** FLIP layout animation (staggered 40 ms, 450 ms spring, `bounce: 0.15`), the credit counter
  rolls, and the roundels scale 0.6→1 (200 ms). About 2 s total, then still.
- **Tech:** Motion `layout`/`layoutId` (shared with the real `PitchView`, so the hero *is* the
  builder preview). About 15–30 KB gz for Motion. Alternatively, View Transitions API with CSS only (0 KB,
  Chromium/Safari 18+, instant in Firefox fallback).
- **Performance:** 22 DOM nodes and transforms only. The risk is CLS if the pitch size is not reserved,
  so give it a fixed aspect-ratio box.
- **Reduced motion:** show the final pitch immediately with a 120 ms fade.
- **Verdict:** this is the strongest *product* story, but it duplicates the Fantasy tab and is weak before
  the XI is meaningful (pre-season, off-days). **Use it as the transition** when the owner presses
  "Build my XI" (Home → Builder), not as the hero.

#### Concept C: "Ball Field" (data particle field)

Every ball of the head-to-head history between today's two teams (≈ 4 000 balls) is a particle.
Dots are faint, 4s violet, 6s gold, wickets red. The particles drift in from noise and settle into the shape of
the **average worm** of the fixture (two curves in team colours), then breathe very slowly.

```
┌───────────────────────────────────────────────┐
│  ·  ·   ·  .   ·    .  ·  ·  ·   · ·  ··••••  │
│   ·  .    ·   ·  ··  ·    ·  ··••••••••       │  ← particles settle
│ ·   ·  ·    ··  ·   ··••••••••   (MI worm)    │    into worm curves
│     ·   ··  ·••••••••••    ·   ·              │
│  ··••••••     (CSK worm)   ·   ·              │
│  CSK 17–20 MI · 4 112 balls · avg 1st inns 176│
│            [NEXT MATCH CARD overlays right]   │
└───────────────────────────────────────────────┘
```

- **Tech:** **Canvas 2D** with a typed-array particle system (about 3 KB of own code). WebGL via
  `ogl` (about 9 KB gz) only if more than 10 k particles. **Not** three.js/react-three-fiber
  (about 150–200 KB gz, overkill for 2D dots). Pause with `IntersectionObserver` and
  `visibilitychange`, cap at 30 fps on mobile, and use DPR ≤ 2.
- **Reduced motion:** a single static frame of the settled worm, pre-rendered as SVG.
- **Verdict:** the most "2026 generative" look, but the most expensive to tune, it carries a battery cost,
  and it is less legible as data. Keep it as an optional "H2H page header" experiment.

**Not recommended:** Lottie/Rive hero illustrations. They are designer-authored rather than data-driven,
and they add 50–80 KB of runtime (lottie-web light about 50 KB gz, Rive WASM about 80 KB). We may use Rive *only*
for the app loader if a hand-animated version is wanted later.

### 7.2 Loading and transition system

#### Timing rules (all async UI)

| Wait | Show | Rule |
|---|---|---|
| < 150 ms | nothing | Avoid flashes. TanStack Query keeps previous data (`placeholderData: keepPreviousData`). |
| 150 ms – 1 s, page/section data | **Skeleton** mirroring the final layout | Never a centred spinner over a blank page |
| > 300 ms, a user action (save, re-optimise) | **Inline loader** inside the control/bar (stumps & bails) | The control stays in place, and the label changes ("Re-optimising…") |
| > 800 ms, cold start / whole route with no layout yet | **App loader** (seam spin) | **Minimum visible 600 ms** once shown (no blink), then cross-fade 200 ms |
| > 8 s | Add text: "Taking longer than usual" + Retry | Keep the loader |
| > 15 s or error | `ErrorState` with the cause, the last good data timestamp, and Retry | Never infinite |
| Background refetch | Only the `FreshnessBadge` pulses once when new data lands | No loaders for background work |

#### Loaders (prototype: `docs/design/loaders.html`)

1. **Seam spin (app-level).** A white T20 ball whose seam rotates about the vertical axis (SVG,
   CSS `scaleX` 1→−1→1, 0.9 s linear), with a slight tilt sway. Label "Loading match data…".
   Pure CSS/SVG, 0 KB. Used in `app/loading.tsx` only for cold start, and on the PWA splash.
2. **Stumps & bails (inline/action).** Three stumps and two gold bails that hop and settle (1.4 s
   loop). 28 px inside the sticky builder bar and buttons. Pure CSS.
3. **Floodlight sweep skeleton (data pages).** Blocks are `--surface-2` with a 6% light band
   sweeping diagonally every 1.6 s (a stadium light passing over). Skeletons are built per page in
   `loading.tsx` / Suspense fallbacks with **the same grid, row heights and badge sizes** as the
   final page, so CLS stays at 0.
4. **Scoreboard roll (value change, not a loader).** Changed numbers (projected total, credits,
   points, NRR) roll digit-by-digit in 300 ms like a stadium scoreboard.
5. **Rejected:** a bat-swing loader. It is figurative, hard to read at 24–56 px, and it looks like a
   game ad.

#### Route and tab transitions

- **Routes:** a 160 ms cross-fade via the View Transitions API (React `<ViewTransition>` / Next.js
  `experimental.viewTransition`, where supported, otherwise instant). **Shared elements:** match card →
  match hero (team badges and score morph), player row → profile header (badge + name), Home "Build my
  XI" → builder (Concept B assembly).
- **Match tabs:** content swaps instantly, and only the underline slides (200 ms). Tab content
  prefetches on hover/focus (TanStack `prefetchQuery`), so most tab switches never show a skeleton.
- **Sheets:** slide up 320 ms emphasised-decelerate. Exit 200 ms accelerate. Drag-to-dismiss.

#### Optimistic UI (builder)

- Lock, exclude, set C/VC and add/remove apply **instantly** to local state (`useMutation`
  `onMutate`). The affected token gets a dashed gold ring (= pending), and builder-bar numbers show
  `≈` while the server re-optimises.
- The risk slider and what-if switches are **debounced 250 ms**, and the in-flight request is cancelled
  (`AbortController` via the query `signal`). Only the latest result is applied.
- When the response arrives: diff animation (§2.8), numbers roll, the `≈` goes away, and
  `aria-live` announces "XI updated: 2 changes, projected 612".
- On error: roll back to the snapshot, show a toast "Couldn't re-optimise. Your XI is unchanged",
  and offer Retry. Locks the user set stay set.
- Target: the server re-optimise is < 1 s (PLAN §3). If it is slower than 300 ms the inline stumps loader appears,
  and it never blocks further taps (requests queue and the last one wins).

#### Reduced motion (applies to all of §7)

`prefers-reduced-motion: reduce` → no draw-ins, flips, rolls, sweeps, spins or shared-element
morphs. Loaders become a static icon with a gentle opacity pulse (1.2 s, opacity 1→0.55), which keeps
the system-status signal without movement. Heroes render their final frame. Skeletons are static blocks.

---

## 8. Implementation notes (for when `web/` work starts)

1. Replace the neutral tokens in `globals.css` with §2.1–2.2 (keep shadcn variable names, and add
   `--surface-2/3`, `--brand`, `--positive/negative/warning/info`, `--faint`, and the tier ramp). Set
   `defaultTheme="dark"`.
2. Add Saira (`axes: ["wdth"]`) as `--font-display` → `--font-heading`, and a `.num` utility
   (`tabular-nums lining-nums`).
3. Extend `TeamTheme` with `chartDark`, `chartLight`, `chartAlt?`, and add `pickMatchColours(a, b, theme)`
   implementing the clash rule (unit-tested).
4. Restyle the existing `TeamBadge`, `RoleChip`, `RangeBar`, `PitchView` and `FreshnessBadge` before
   building new screens, so every new screen inherits the grammar.
5. Update the nav to Home / Matches / Build / Table / More, with routes per §3.1.

## 8. Owner decision: landing hero (2026-10-02)

**Rotate by match state** (prototypes in `docs/design/`):
- **Before a match** (fixture known, until result): **B, XI assembles**. Shows the predicted XI with C/VC and projected total,
  switching from "Provisional" to "XI confirmed" at toss. CTA → Build.
- **After a match** (until the next fixture's toss window): **A, wagon wheel** of the last match's top innings when
  official shot data exists (2025+). Otherwise **C, particle worm** of the last match.
- Off-season: C on the season final.
All three share the next-match card and honour prefers-reduced-motion with static final frames.
