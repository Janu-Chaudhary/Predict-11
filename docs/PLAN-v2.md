# Predict-11 v2 — Rebuild Plan

_Drafted 2026-10-01 from four parallel research tracks: live data sources, competitor features/UX,
ML modelling, system architecture. Status: proposal — decisions marked ❓ need the owner._

---

## 0. Where we are and why rebuild

| Area | v1 today | Problem |
|---|---|---|
| Data | Cricsheet YAML, manual download | ~1-day lag (median, measured: 0–11 days), no live, no announced XI before toss |
| Identity | players keyed by name string | breaks across sources; no registry |
| Squads/credits | hand-scraped CSVs with inconsistent headers | stale, manual |
| Model | LightGBM on 15 form features | **565 vs 562** for a plain last-5-form rule — statistical noise; early-stopping uses the test set, so even that is optimistic |
| Live serving | uses each player's stale pre-last-match snapshot | ignores latest match, wrong venue/opponent context |
| Optimizer | one XI, mean-only | no locks/excludes, no multi-lineup, no risk/variance, no ownership |
| UI | one 133-line HTML page | one table, no interactivity |

**Market context:** India's 2025 Online Gaming Act ended real-money contests; Dream11 is now
free-to-play/second-screen. Paid "tips" lose value; **transparency, education, live engagement and
free power-tools** (multi-lineup, sims) gain value. Position v2 as an *open, honest analytics
companion*, not a "guaranteed win" tipster.

---

## 1. Data ingestion — replacing the Cricsheet dependency (Phase 1–2, do first)

### Research findings (measured / verified by the research agent)
- **Cricsheet is not the bottleneck it seemed**: median publish lag 1 day; rolling feeds
  `recently_added_{2,7,30}_json.zip`; includes impact-player `replacements`. But it is **never
  same-day and never live**, and withholds some matches → cannot be primary in-season.
- **Official IPL feed (`ipl-stats-sports-mechanic` / `scores.iplt20.com`) is gone** (NoSuchBucket).
- **ESPNcricinfo internal API is Akamai-blocked** (403); scrapers need headless browsers and break.
- **Licensed APIs** (2025-26 pricing):

| Source | Ball-by-ball | Live | XI/toss | Price | Verdict |
|---|---|---|---|---|---|
| **SportMonks Cricket** | ✅ | ~1 min | ✅ | **€29/mo** (Major, incl. IPL), 14-day trial | **Primary** — cheapest licensed full feed |
| CricketData.org (CricAPI) | claimed | few min | ✅ | free 100 hits/day; $6–65/mo | Cheap fallback / cross-check |
| Roanuz | ✅ | push | ✅ + fantasy credits | ~₹16k+/mo | Upgrade path if credits needed |
| EntitySport | ✅ | ✅ | ✅ + credits | $250–450/mo | Upgrade path |
| Sportradar | ✅ | lowest | ✅ | sales-led, ~$500+ | Overkill |
| Cricbuzz/Cricinfo scraping | ✅ | ✅ | ✅ | free | Legal + breakage risk → flag-gated, personal use only |

- **Dream11 credits & selection %**: no public API; vendor "credits" are unconfirmed to equal
  Dream11's. → credits = user-editable input (prefilled from vendor if available);
  ownership = **our own model output**.
- **Weather**: Open-Meteo (free, non-commercial, no key) for dew/humidity at match time.

### Target design
```
              ┌──────────── SourceAdapter protocol ────────────┐
              │ fixtures() squads() toss_xi() deliveries()     │
              └───┬──────────────┬───────────────┬─────────────┘
         SportMonks (primary)  CricAPI (fallback)  Cricsheet (backfill + truth)
              │                  │                    │
              ▼                  ▼                    ▼
        raw archive (gzipped payload + hash) ──► normalize ──► DQ checks ──► Postgres canonical
                                                                 (quarantine on fail)
```
- **Player registry**: Cricsheet `people.csv` identifier = internal key (18.5k people, 18.5k with
  cricinfo IDs). `player_source_id(source, key)` table; vendor IDs mapped once per season by fuzzy
  name + team/squad + DOB; unknowns → **manual review queue** (never auto-create); override CSV.
- **Reconciliation**: daily job pulls Cricsheet `recently_added_2`; when a match lands it becomes the
  canonical record; diff runs/wickets/points vs vendor and alert on mismatch.
- **Schedule (APScheduler worker)**: fixtures+squads daily · T-60min→toss every 2 min (XI/toss/impact
  subs) · in-play every 30 s · post-match finalize + review · weekly retrain.
- **Idempotency**: natural-key upserts, payload hash dedupe; re-ingest = zero diffs.
- **DQ**: ≤20 overs/≤10 wkts per innings, delivery sum = scorecard total, 11(+impact) per XI,
  100% player resolution.

---

## 2. ML upgrade (Phase 3 & 7)

Ranked by impact/effort:

1. **Fix evaluation (prerequisite)** — rolling-origin by matchday over 2023–25(+26), inner time-based
   validation for early stopping, paired bootstrap CIs (current 3-pt gap is noise; SE ≈ ±5–8).
2. **Opportunity features from the announced XI** — expected batting slot, opener/finisher,
   powerplay/death bowler, impact-sub flag, `era>=2023` (impact rule added ~12–15 runs/innings).
   _Biggest single lever: opportunity drives most fantasy variance._
3. **Point-in-time live features** — recompute after every match; use fixture's real venue/opponent.
4. **Quantile outputs (p10/p50/p90)** — LightGBM quantile heads → floor/ceiling, powers SL vs GL.
5. **Decomposed model** — P(bats), balls faced, P(bowls), overs × shrunk per-ball rates, scored
   through the existing `fantasy_points.py` (handles milestones & rule changes exactly).
6. **Cold-start via all-T20 Cricsheet data** (internationals + other leagues) with league-strength
   adjustment + empirical-Bayes shrinkage.
7. **Context**: venue par score, pace/spin wicket share, toss/chase bias, dew (evening × venue ×
   humidity), batter-vs-bowler-type matchups (shrunk).
8. **Monte Carlo match simulator** (10k sims, ball-level) → per-player distributions + teammate
   correlation matrix → enables GL optimization.
9. **Ownership model** (credits + form + fame proxy) → leverage/differentials.

**Optimizer modes**: _Safe (SL)_ = mean − λσ, C/VC on high floor · _Balanced_ = mean ·
_Contrarian (GL)_ = maximize P(top-1%) over sim scenarios, ownership fade, correlation stacks,
N-lineup portfolio with exposure caps and min-unique overlap.

**MLOps**: MLflow runs with data version + config hash; champion/challenger — promote only if the
rolling backtest beats the champion; CI guard fails on >5% MAE regression.

---

## 3. Product features

| Feature | Tag | Notes |
|---|---|---|
| Fixture list with data-freshness badge | must | "Pre-toss projection" vs "Lineups confirmed ✓ 19:02" |
| Player cards: range bar (floor–median–ceiling), form sparkline, venue split, ownership chip | must | ranges, not false-precision numbers |
| Pitch-view team builder (WK/BAT/AR/BOWL rows, C/VC badges, credits bar) | must | table view one toggle away |
| Lock / exclude / force-captain, max-per-team, re-optimize instantly with diff highlight | must | every competitor has it |
| **Single risk slider** Safe ↔ Balanced ↔ Contrarian | differentiator | drives quantile target + ownership fade + correlation |
| Multi-lineup portfolio (N teams) + exposure heatmap + C/VC rotation | must (free here, paid elsewhere) | |
| "Why this player" chips (top-3 SHAP drivers in plain words) | must | "Opens at Chepauk · strong vs spin · dew favours chase" |
| Auto re-projection at toss/XI announcement + push/notification | must | the payoff of same-day data |
| Impact-player intelligence: likely 12th man / likely subbed-out | must | |
| Pitch & conditions card: par score, pace/spin split, chase bias, dew/weather | must | |
| **Rate My Team**: paste/build an XI → projected percentile + best swaps | differentiator | |
| **What-if toggles**: toss winner, dew on/off, pitch type → instant re-opt | differentiator | |
| Live score + live fantasy points via a **light poll** (re-approved 2026-10-02, see FEATURE-CATALOG §7); full data still from post-match harvest | must | |
| **Post-match review**: predicted vs actual per player, your XI's rank vs simulated XIs | must | |
| **Public backtest/accuracy page**: per-season results vs baselines, captain hit-rate, calibration | differentiator | trust signal; rival CricJosh publishes 31.4% top-2 captain rate |
| Head-to-head: batter vs bowler-type matchups with confidence | differentiator | |
| LLM match preview (150 words, generated **only** from structured features) | nice | |
| Late swap after toss | nice | |
| Saved teams / accounts | nice | Phase 8+ |

### UI/UX principles
1. Mobile-first, one-thumb: bottom-sheet player cards, sticky "credits left · roles valid" bar.
2. Pitch view is the default; table is secondary.
3. Show uncertainty honestly (ranges, confidence) — never "guaranteed".
4. One risk control on the surface, advanced knobs behind a disclosure.
5. Data recency always visible (timestamp + freshness badge).
6. Tap a player → lock / exclude / details; every change re-optimizes in <1 s with a visible diff.
7. Trust signals everywhere: accuracy badge linking to the backtest page.
8. Dark mode, team colours, fast (<2 s LCP on 4G).

---

## 4. Architecture

```
predict11/
├─ backend/  (uv, Python 3.12)
│  ├─ src/p11/{core, registry, ingest/{sources,archive,normalize,quality},
│  │            scoring, features, model, sim, optimize, jobs, api}
│  ├─ migrations/ (Alembic)
│  └─ tests/{unit, integration, golden}
├─ web/      Next.js (App Router) + Tailwind + shadcn/ui + TanStack Query, typed client from OpenAPI
├─ infra/    docker-compose (caddy, api, worker, postgres, web), backups
└─ .github/workflows/ (ci, deploy)
```
- **Storage**: Postgres = system of record (registry, fixtures, scraped deliveries, predictions,
  lineups). Nightly export to a Parquet lake read by **DuckDB** for training/backtests.
- **API (`/api/v1`)**: `fixtures`, `fixtures/{id}/players`, `players/{id}`, `POST fixtures/{id}/lineups`
  (strategy, n, locks, excludes, min_unique), `lineups/{id}/explain`, `fixtures/{id}/review`, `backtest/runs`, `meta/freshness`,
  token-protected `admin/*` (job triggers, registry review).
- **Deploy**: one Hetzner VPS (~€5/mo) with docker-compose — the worker must run continuously during
  matches, which serverless handles poorly. Alt: Vercel (web) + Fly/Railway (api+worker) + Neon.
- **Observability**: structlog, Sentry free tier, Healthchecks.io dead-man pings per job, freshness
  badge, uptime monitor.
- **Tests/CI**: unit (scoring, optimizer, matcher) · golden payload snapshots per source ·
  cross-source test (Cricsheet points == scraped points for same match) · testcontainers Postgres
  idempotency · model-regression guard · Vitest + Playwright smoke.

---

## 5. Phased roadmap

| Phase | Deliverables | Exit criteria |
|---|---|---|
| **0 Foundations** (~1 wk) | monorepo, uv, Alembic, compose, CI; port scoring + optimizer + tests; fix eval leak | CI green, `/health` up |
| **1 Registry + backfill** | people.csv registry, Cricsheet adapter → Postgres → Parquet, raw archive, DQ | 2008–2025 loads idempotently; 100% players resolved; points == v1 labels |
| **2 Scraper ingestion** | adapters for Cricbuzz, ESPNcricinfo (Playwright), iplt20.com, CricketData.org; toss-snapshot + post-match-harvest jobs; merge/cross-check; Cricsheet reconciliation; review queue | replay 3 archived 2026 matches → points within ±1 of Cricsheet; ≥2 sources agree on totals; XI captured before match start; alert on scraper break |
| **3 Prediction service** | rolling-origin eval, opportunity + context features, quantile heads, point-in-time refresh at toss | beats last-5-form with bootstrap CI excluding 0; refresh ≤2 min after toss |
| **4 Core UI** | fixtures, player cards, pitch builder, lock/exclude, single optimal XI | valid XI built on mobile in <60 s |
| **5 Power tools** | risk slider, multi-lineup + exposure, explanations, Rate My Team, what-if | 20 lineups <3 s, diversity constraint honoured |
| **6 Review** | post-match review (predicted vs actual, your XI's rank vs simulated XIs) | review auto-generated ≤1 h after match from scraped data |
| **7 Advanced ML** | decomposed model, all-T20 cold start, Monte Carlo sim, ownership model, GL optimizer, public backtest page | GL backtest: higher top-1% rate vs mean-optimizer |
| **8 Polish** | LLM preview, notifications, accounts/saved teams, late swap | — |

**Season timing**: IPL 2027 likely starts ~late March 2027 → Phases 0–4 should land by **Feb 2027**
so the scrapers can be shaken out on other T20 leagues/internationals before IPL.

---

## 6. Decisions (answered 2026-10-01)

| Question | Decision | Consequence |
|---|---|---|
| Data budget | **Free sources only** | No SportMonks; build the adapter layer so a paid source can drop in later |
| Audience | **Personal tool** | Scraping acceptable for own use; Open-Meteo free tier OK; no accounts/auth; run locally or on a ~€5 VPS |
| Repo | **This repo, tag `v1`** | Restructure into `backend/` + `web/`, port scoring/optimizer/tests |
| Frontend | **Next.js + shadcn/ui** | as in §4 |

### Data design — scraping only, post-match first (supersedes §1 vendor recommendation)

Decisions (2026-10-01, follow-up): **no paid APIs, no live in-match scraping** (amended 2026-10-02: a light live-score poll is allowed — see FEATURE-CATALOG §7). Scrape each match
**after it completes**, plus **one toss-time scrape** for the announced XI. Use **every free source
available** and merge them, so no single site is a point of failure.

**Three scrape triggers per match**

| Trigger | When | What | Requests |
|---|---|---|---|
| Daily sweep | once a day | fixtures, squads, venue, injuries/replacements | ~10 |
| Toss snapshot | T-35 → T-25 min, retry every 2 min until found | toss result, announced XI + impact subs, batting order | 2–5 per source |
| Post-match harvest | ~30–60 min after result, retry hourly for 12 h | full scorecard, ball-by-ball commentary, fielding, impact subs used, POTM | ~5–20 per source |
| Reconciliation | daily | Cricsheet `recently_added_2` → canonical record when it lands (~1 day) | 1 zip |

**Role split (confirmed by owner):** Cricsheet 2008→2026 = **model training history** (full,
clean coverage) + canonical reconciliation. Scrapers = **same-day** data for the current season
(toss XI + post-match harvest) until Cricsheet catches up. Priority order of work: scrapers first.

**Dream11 credits:** fixed per player per season → `season_credits(season, player_id, credits)`.
Owner supplies them each season. Stored today: 2025 only (223/226 players, `data/raw/Teams`).
For now 2025 credits stand in for 2026; revisit later.

**Player identity — never join on names.** Cricsheet uses short names ("V Kohli", "RG Sharma")
while scrapers use full names ("Virat Kohli"). Every Cricsheet match carries
`info.registry.people` (e.g. `V Kohli: ba607b88`) → that 8-char ID is our internal player key.
- ESPNcricinfo → exact join via `people.csv` `key_cricinfo` (≈99.8% coverage).
- Cricbuzz / iplt20 → one-time matcher, constrained to that team's squad: surname match +
  initials consistent with full name ("Rohit Gurunath Sharma" ⇒ "RG Sharma"), + role/DOB when
  available; result stored permanently in `player_source_id`; ambiguous → review queue;
  `overrides.csv` for manual fixes.
- Display names come from scrapers; all joins use the ID.

**Prediction flow around the toss (the playing XI drives the final team)**
1. *Before toss* — provisional projection from the full squads, each player weighted by a
   modelled P(plays). Shown as "Provisional".
2. *Toss snapshot* — scrape toss winner/decision, **both playing XIs, impact-sub lists, batting
   order** from all sources; merge; verify each side has 11 (+ subs) resolved to registry IDs.
3. *Re-predict* — candidate pool = the 22 confirmed players (+ likely impact subs); recompute
   features with real batting slot, bat-first/chase, toss; rerun optimizer. Shown as
   "Lineups confirmed ✓ HH:MM". Target: within 2 min of the XI being found.
4. If no source has the XI by match start → keep provisional projection and flag it.

> **Updated after real probes:** see `docs/SCRAPING-SPIKES.md` — its "Resulting source strategy"
> table supersedes the source table and merge priorities below (iplt20/stats.bcci.tv for XI,
> ESPN API for ball-by-ball, Cricinfo IDs as the ID bridge).

**Free sources, all as adapters behind one `SourceAdapter` interface**

| Source | Method | Gives us | Role |
|---|---|---|---|
| **Cricbuzz** | internal JSON endpoints (no browser needed) | scorecard, commentary ball-by-ball, XI, toss | primary same-day |
| **ESPNcricinfo** | Playwright (CDN-blocked for plain HTTP) | richest ball-by-ball, XI, impact subs; match ID == Cricsheet file ID | secondary same-day + ID bridge |
| **iplt20.com** | HTML/JSON of new site (backend to be reverse-engineered in Phase 2 spike) | official XI, squads, impact subs | tertiary / squads |
| **CricketData.org free** (100/day) | REST | fixtures, squads, scorecard | fixtures + scorecard cross-check |
| **Cricsheet** | JSON zips + `people.csv` | ball-by-ball, XI, registry | **canonical truth** + 2008→ backfill |
| **Open-Meteo** | REST, no key | humidity/dew/temperature at venue | conditions features |

**Merge rules**
- Each field has a source priority; e.g. ball-by-ball: Cricsheet > ESPNcricinfo > Cricbuzz;
  toss/XI: iplt20 > ESPNcricinfo > Cricbuzz; fixtures: CricketData.org > Cricbuzz.
- Cross-check across sources: innings totals, wickets, each player's runs/balls/wickets/catches.
  Agree → `verified`; disagree → keep highest-priority value, flag `conflict`, show in admin view.
- Fantasy points are computed from the merged record; when Cricsheet arrives, recompute and
  log any point deltas (should be ~0 — this is the scraper-accuracy test).
- Every raw response archived (gzip + hash) → scrapers can be fixed and replayed without
  re-hitting sites. Golden-payload tests per source catch HTML/JSON format changes.
- Politeness: low request rates, caching, backoff, realistic User-Agent, for personal use.
- Credits: entered/edited per match in the UI (prefilled from last match); ownership modelled.

**What this removes from the plan:** live SSE tracker, in-play polling, LISTEN/NOTIFY.
Replaced by: toss-time re-projection + a richer **post-match review** available ~1 h after the match.

## 7. Risks
- Vendor impact-player/toss field coverage unverified until trial → validate in Phase 2 trial window.
- Vendor credits may ≠ Dream11 → keep credits editable; don't hard-trust them in the budget constraint.
- Cross-vendor name matching errors → manual review at auction/replacement windows.
- Model gains may stay modest — fantasy is high-variance; the product's value must also come from
  tooling, speed and transparency, not only accuracy.
