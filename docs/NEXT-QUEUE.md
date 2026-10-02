# Predict-11 v2 — Next queue

_Updated 2026-10-02. Everything above this line in git history is built, verified and committed
(see `git log v1..v2`). Items are ordered by priority within each block._

## Done so far (summary)
- Data: scrapers proven on all 74 IPL 2026 matches (stats.bcci.tv primary, ESPN ID bridge,
  Cricbuzz cross-check), Cricsheet 2008–2026 backfill (1,243 matches), player registry with
  full display names, roles/batting hand/bowling type, photos (cached WebP), start times,
  weather for every match, fantasy points for every match (40/40 vs published Dream11 totals).
- Backend APIs: seasons/table/NRR (matches official 2026 table), playoff scenarios, story,
  records, teams, players, compare, H2H, venues, milestones, streaks, bowling-type matchups,
  conditions/dew, fantasy distributions, leaderboards, hindsight best XI (HiGHS ILP), home hero.
- Web (Floodlight): Home (rotating hero), Table, Records, Teams, Players, H2H, Venues, Fantasy,
  loaders, ⌘K search, dark/light.

## Q1 — Small gaps — DONE (d5b3f4c)
Fantasy display names/photos/last10/backend C-VC, pitch photos, Fantasy bento tile, season-scoped
matchup splits, ⌘K venues + popular players, query indexes (migration e1a7c3d90b42).
Also: team **Squad** tab (`/teams/{id}/squad`, latest-season roster + 2025 squad list,
overseas flag in `season_credits`), frameless player cut-outs everywhere, full-height profile
photo.

## Known issues
- `test_endpoints_respond_fast_when_warm[/players/compare]` runs ~330–440 ms vs a 300 ms budget
  (also fails without the new indexes; check with the dev servers stopped).
- CSK squad CSV has no Ruturaj Gaikwad row (no credits for him). 2026 squad CSVs needed to drop
  released players from the Squad tab.
- Photos are cached at 256 px: slightly soft at the 176 px profile size on 2x screens; a 512 px
  cache variant would need a re-download of the originals.

## Q2 — Production scrapers + match centre (Phase 2–3)
1. Promote spike scrapers to `p11.ingest.sources` adapters (BCCI, ESPN, Cricbuzz, Hindu) with raw
   archive, golden-payload tests, retries/backoff, `Edak` key auto-recapture.
2. `fixture` table + daily fixtures/squads sweep (next-match countdown, Home hero B pre-match).
3. Toss-time job (T-35 → start): XIs, impact subs, batting order → re-projection trigger.
4. Post-match harvest job → per-source `match_source` rows → **per-field majority vote**
   (`field_conflict`), Cricsheet as one vote when it lands; recompute fantasy points.
5. Light live poll (BCCI live_scores/scorecard/bbb?size=12 every 60 s; Cricbuzz miniscore
   fallback): score, batters, bowler, last 12 balls, DRS reviews.
6. Ingest official wagon-wheel (Ellipse `/wagon`, 2025+) into the DB → Home hero A for real.
7. Match centre UI `/matches/[id]`: summary, live, scorecard, ball-by-ball, XIs, charts
   (worm, Manhattan, partnerships, wagon wheel, win probability, over momentum), conditions
   (`/matches/{id}/conditions`), live fantasy points, DRS.
8. Scheduler worker (APScheduler) + healthchecks + `/meta/freshness`.
9. **Test on the next live T20** (any series): XI publish timing per site, live poll cadence
   (`spikes/live/06_poll_freshness.py`), retired-hurt handling.

## Q3 — ML model + fantasy tools (Phase 3 & 7)
1. Rolling-origin evaluation (no test-set early stopping), paired bootstrap CIs; baselines:
   last-5 form, naive captain (9.6% top-2 hit-rate in 2026).
2. Features: announced XI + batting slot, role/phase usage, impact-player era, venue par
   (recent-weighted), bowling-type & batting-hand matchups (shrunk), toss/chase, dew, rest days.
3. Model: opportunity × rate decomposition or LightGBM quantile heads (p10/p50/p90); cold start
   from Cricsheet all-T20 data.
4. Optimizer modes on `p11.optimize.xi`: safe / balanced / contrarian; captain picker with
   P(top-2); multi-lineup portfolio with exposure caps; ownership estimate; locks/excludes.
5. UI: `/build` builder (pitch + list, risk slider, why-this-player chips), Rate My Team,
   what-if toggles (toss, dew).
6. Monte Carlo match simulator for grand-league portfolios (later).

## Q4 — Review & accuracy (Phase 6–7)
1. Post-match review: predicted vs actual per player, your XI's rank vs simulated XIs.
2. `/accuracy` page: per-season MAE, captain hit-rate, range calibration vs baselines.

## Q5 — Data quality & backlog
- Real start times 2008–2024 via ESPN events API (`core.espnuk.org/v2/sports/cricket/events/<id>`).
- 50 unmatched 2025 squad/image names; store BCCI↔Cricsheet ID mapping in `player_source_id`.
- Per-season player roles (currently one current role for all seasons).
- Pre-2024 Dream11 rule sets (pre-2025 points use T20_2024 as an approximation).
- `player_match_points` keyed by rules version if multiple rule sets are needed side by side.
- Weather is gridded reanalysis (not at-ground); dew finding (no chase advantage) to revisit.
- Credits: owner supplies each season (2025 stands in for 2026).

## Q6 — UI polish backlog
- Route view transitions, colour-contrast token test, collapsing match header.
- Points table: projected-finish heat row, next-fixture column; team pages: season comparison.
- H2H modes: team v team, player v team.
- `/records/loading.tsx` scoping so milestones/streaks get their own skeletons.

## Owner decisions pending
- Remove v1 code from the tree (`src/`, `tests/`, `frontend/`, old `pyproject.toml`); it is
  preserved at tag `v1`. Blocked earlier by the permission system — owner to run
  `git rm -r src tests frontend pyproject.toml` if wanted.
- Before making the repo public: remove the public `Edak` widget key from `spikes/`.
