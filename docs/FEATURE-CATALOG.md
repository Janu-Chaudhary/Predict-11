# Predict-11 v2: Feature Catalog and Feasibility Check

Written 2026-10-02 on branch `v2`. Builds on `docs/PLAN-v2.md` §3 and `docs/SCRAPING-SPIKES.md`.
Every "Have?" claim below was checked against the local Postgres (`p11@localhost:5433`). The
queries and their results are in [§4 SQL evidence](#4-sql-evidence). Fantasy points came from
running the verified scorer (`backend/src/p11/scoring`) over every 2025 and 2026 match in the DB
(74 + 74 matches, 1,628 player-rows each). The scoring script lives in the session scratchpad.
None of these numbers are stored in the DB yet.

**Legend**
- **Have?**: ✅ in DB now · 🟡 proven scrapeable (spike) but not ingested · 🔴 no source / gap
- **Effort**: S ≤ 3 days · M ≈ 1–2 weeks · L > 2 weeks (one developer)
- **Phase**: matches PLAN-v2 §5 (0 Foundations · 1 Registry · 2 Scrapers · 3 Prediction · 4 Core UI · 5 Power tools · 6 Review · 7 Advanced ML · 8 Polish). **4a** is a new slot proposed here. It holds analytics pages that need only the DB plus the API, not the model.
- **Tag**: must-have · differentiator · nice-to-have

---

## 1. Verified data inventory (what the catalog stands on)

| Asset | Verified state | Notes / gaps found |
|---|---|---|
| Matches | 1,243 (2008–2026, 19 seasons; 2026 = 70 league + Q1/Elim/Q2/Final) | `result` ∈ win/tie/no_result (9 NR, 23 D/L). **No start time column** → day/night and afternoon double-header split is not possible yet |
| Deliveries | 295,732 incl. non-striker, extras breakdown, wicket kind, fielders, `non_boundary` | `over` 0–19; super-over flagged |
| Innings | 2,514; 34 with reduced `target_overs` | Needed for correct NRR in DLS games |
| Lineups | 26,789 XI rows, 557 impact-in/out pairs (2023–26: 139/137/141/140 per season), 197 sub-fielders | Impact-player history is complete |
| Toss | winner + decision on every match | |
| Venues | 36 canonical (60 aliases) | |
| Players | 18,554 registry; source IDs: cricinfo 18,613 · bcci 1,329 · **cricbuzz 50** | The brief said "cricbuzz IDs for 18.5k". In fact only 50 are mapped, so Cricbuzz still needs the squad-constrained matcher |
| Player attributes | **none in DB**: no role, batting hand or bowling style | Role is required by the scorer (duck/SR rules). Cricbuzz series-squad JSON has `battingStyle`/`bowlingStyle` (seen in `spikes/cricbuzz/samples/06_series_squad_99705.json`). The iplt20 squad CSVs have Role |
| Credits | `season_credits` = 199 rows, 10 teams, **2025 only** | 2026 credits are missing, so any credit-constrained 2026 result is approximate |
| Fantasy points | Computable for every match (scorer verified against 40 published 2026 totals) | **Not persisted**. A `player_match_points` table is the first enabler for ~10 features below |
| Same-day sources | stats.bcci.tv (74/74 toss/XI/innings), Cricbuzz, ESPN; Ellipse `/wagon` (2025+), `/manhattan`, `/winviz_history`; Open-Meteo; Hindu live-score API (`livescoreapi.thehindu.com/api/cricket/{current,current-scorecard,scorecard,commentary,grouped/fixtures,wagonwheel,runrate,matchstats}`) | All 🟡: proven in spikes, no tables yet |
| Cold start | 37 of 204 players who played in 2026 debuted in 2026 (60 debuted 2025–26) | Supports downloading the Cricsheet all-T20 data |

---

## 2. Feature catalog (30 features)

### A. Match centre

| # | Feature | User value (one line) | Data needed → Have? | Effort | Phase | Tag | Risk |
|---|---|---|---|---|---|---|---|
| A1 | **Match centre**: fixture card → toss & decision → confirmed XIs + impact subs → live score/status → result | One screen tells you where the match stands and whether lineups are out, so you can stop refreshing three apps | Fixtures 🟡 (bcci); toss/XI/subs 🟡 (bcci scorecard, 74/74); live score/status 🟡 (Hindu `current`, `current-scorecard`); history ✅ | M | 2 + 4a | **must-have** | PLAN §6 says "no live in-match scraping". A light poll of one score endpoint (≈1 req/min) is a scoped exception the owner must approve. The Hindu API is unofficial. When the XI appears before a live match is still untested |
| A2 | **Pre-match preview card**: team H2H record, venue par, toss tendency, dew forecast, 3 key matchups, optional LLM 150-word summary | Everything you'd research in 20 minutes, on one card | H2H/venue/toss ✅; dew forecast 🟡 (Open-Meteo); start time 🔴 (scrape) | M (S without LLM) | 4a / 8 (LLM) | must-have | The LLM must be fed only structured facts to avoid hallucination |
| A3 | **Post-match scorecard + charts**: Manhattan, worm, win-probability swing, wagon wheel, partnerships | Understand *how* the match was won, not just the result | Scorecard/partnerships ✅ (from deliveries); win-prob 🟡 (Ellipse `winviz_history`); wagon 🟡 (2025+ only) | M | 6 | differentiator | Wagon and win-prob depend on Ellipse with `Edak` key rotation. Wagon data does not exist before 2025 |
| A4 | **Live fantasy points (approx.)** from the live scorecard | See your XI's running total during the match | Live scorecard 🟡 (Hindu). Dot balls and maidens may be missing from the live scorecard | M | 8 | nice-to-have | Contradicts the dropped "live tracker". Approximate only, so label it "provisional" |

### B. Teams and squads

| # | Feature | User value | Data → Have? | Effort | Phase | Tag | Risk |
|---|---|---|---|---|---|---|---|
| B1 | **Team squads**: roles, overseas flag, credits, photo, batting/bowling style, IPL career line | Know every player available to a franchise at a glance | Squads/roles/overseas/images 🟡 (iplt20 + Ellipse squads); styles 🟡 (Cricbuzz); career ✅; credits ✅ 2025 only | S–M | 2 + 4a | **must-have** | Mid-season replacements need the daily sweep. Credits for the new season must be entered by hand |
| B2 | **Likely XI & batting order** (P(plays) per player, last-N XIs, impact-sub patterns) | Build your team before the toss with confidence | XIs + impact pairs ✅ (557); batting position derivable ✅ from first appearance in deliveries | M | 3 | must-have | New-season squads have no history for new signings |
| B3 | **Impact-player intelligence**: who usually comes in/out, when, and the fantasy value of a sub | Avoid picking the player who gets subbed out after batting | 557 impact in/out pairs ✅; timing 🟡 (bcci over + time) | M | 3 | must-have | Sub choice depends on toss result, so it is only certain at the toss |
| B4 | **Team form page**: results, run-rate by phase, top fantasy contributors, bat-first vs chase record | See team strength quickly | ✅ | S | 4a | nice-to-have | — |

### C. Players

| # | Feature | User value | Data → Have? | Effort | Phase | Tag | Risk |
|---|---|---|---|---|---|---|---|
| C1 | **Player page**: career/season, **phase-wise SR & economy**, venue splits, form sparkline, fantasy floor–median–ceiling | Judge a player by role and context, not one average | ✅ all from deliveries + scorer (persist points first) | M | 4a | **must-have** | Small samples (e.g. Dhoni powerplay = 5 balls). Show the sample size |
| C2 | **Fantasy leaderboards & consistency**: season totals, mean, SD, p10/p90, points per credit | Find reliable vs boom-or-bust picks | ✅ computed (§4 E6) | S | 4a | must-have | Points per credit is only exact for seasons where we have credits |
| C3 | **Player comparison** (2–3 players side by side, same filters) | Settle "X or Y?" calls | ✅ | S | 5 | nice-to-have | — |
| C4 | **Cold-start profiles** for IPL debutants using all-T20 history | 37 of 204 2026 players had no IPL history; this fills those blanks | Cricsheet all-T20 🟡 (available, not downloaded) | M | 7 | differentiator | Leagues differ in strength, so a league-strength adjustment is needed |

### D. Head-to-head and matchups

| # | Feature | User value | Data → Have? | Effort | Phase | Tag | Risk |
|---|---|---|---|---|---|---|---|
| D1 | **Batter vs bowler H2H**: balls, runs, SR, dismissals, dot%, boundary%, matches, plus a confidence badge | The owner's favourite. Spot the bowler who owns a batter | ✅ (§4 E1: Kohli v Bumrah 108 balls) | S | 4a | **must-have** | Median pair has only **5 balls**. Only 1,615 pairs have ≥30 balls. Shrink toward the bowler-type prior and grey out small samples |
| D2 | **Batter vs bowling type** (right-arm pace, left-arm orthodox, leg-spin, …) and **bowler vs batting hand** | Usable for every matchup, unlike sparse 1-v-1 data | Deliveries ✅; **styles 🔴 in DB** (🟡 Cricbuzz for current squads; retired players need Cricinfo profiles) | M | 3 | differentiator | Style coverage for 2008–2015 players. Needs a one-off profile scrape |
| D3 | **Matchup-of-the-day grid**: cross-join both confirmed XIs, highlight extreme H2H cells | All matchups for tonight in one heatmap | ✅ + XI 🟡 | S (after D1) | 4a | differentiator | Same sample-size caveat as D1 |
| D4 | **Team vs team history** (overall, at venue, last 5) | Context for the preview | ✅ | S | 4a | nice-to-have | Franchise renames are handled by the canonical teams (14) |

### E. Venue and conditions

| # | Feature | User value | Data → Have? | Effort | Phase | Tag | Risk |
|---|---|---|---|---|---|---|---|
| E1 | **Venue card**: par 1st-innings score (recent-weighted), chase win %, toss decision trend, phase run rates, pace vs spin wicket split | Know whether tonight will be a 175 or a 215 ground | ✅ (§4 E2); pace/spin split needs styles 🔴 | S–M | 4a | **must-have** | **Scoring inflation**: powerplay RPO went 7.8 (2022) → 10.1 (2026). Use 2023+ (impact-player era) or recency weights, not all-time averages |
| E2 | **Dew & weather watch**: hourly dew point and humidity at start time, rain risk | Dew favours chasers, which feeds toss and captaincy calls | 🟡 Open-Meteo (proven); start time 🔴 (from fixtures scrape) | S | 2 | must-have | Dew effect not yet measured. Calibrate on 2023–26 night games once weather is backfilled |

### F. Season, points table and playoffs

| # | Feature | User value | Data → Have? | Effort | Phase | Tag | Risk |
|---|---|---|---|---|---|---|---|
| F1 | **IPL points table** (P/W/L/NR/Pts/NRR, form, next fixture) for every season 2008–2026 | The owner's favourite. Instant standings, history included | ✅ (§4 E4: 2026 recomputed, top 4 = actual playoff teams) | S | 4a | **must-have** | NRR must use DLS-revised overs (34 reduced innings). Cross-check against the official table |
| F2 | **Playoff qualification scenarios**: % chance of top 4 / top 2, "what X needs", clinched / eliminated badges, interactive "pick the winners" | The talking point of the last 3 weeks of every season | ✅ results + fixtures 🟡; exhaustive enumeration ≤ ~20 remaining matches, Monte Carlo before that | M | 4a | differentiator | 50/50 outcomes are naive. Weight by a simple team-strength model. NRR ties need NRR simulation |
| F3 | **Season story**: orange/purple cap race, fantasy MVP race, team-of-the-season | Season-long engagement | ✅ | S | 4a | nice-to-have | — |

### G. Fantasy tools (the product core)

| # | Feature | User value | Data → Have? | Effort | Phase | Tag | Risk |
|---|---|---|---|---|---|---|---|
| G1 | **Projections with ranges + optimal XI** (lock/exclude, max-per-team, pitch view) | The main reason the app exists | Features ✅; model ❌ (Phase 3); credits ✅ 2025 only | L | 3–4 | **must-have** | Season credits must be entered. Credits are fixed per season |
| G2 | **Captain / VC picker** with P(top-2 scorer) and a hit-rate badge | Captaincy is ~3× leverage; the C pick usually decides contests | Points ✅ | M | 3–5 | **must-have** | The naive baseline is weak (§4 E5: last-5-form captain hits top-2 only **9.6%** of 2026 games), so the bar to beat is clear |
| G3 | **Multi-lineup portfolio** + exposure heatmap + C/VC rotation | Cover outcomes in grand leagues | Projections | M | 5 | must-have | Diversity vs quality trade-off |
| G4 | **Risk slider** (Safe ↔ Contrarian) | One knob instead of ten | Quantile model + ownership | M | 5 | differentiator | Depends on G6 |
| G5 | **"Why this player"** chips (top-3 drivers in plain words) | Trust the pick | Model SHAP | M | 5 | must-have | — |
| G6 | **Ownership estimate & differentials** | Find low-owned players who score high | 🔴 **no real ownership data**. Proxy model from credits, form, popularity, team | L | 7 | differentiator | Cannot be validated: Dream11 publishes no ownership. Spot-check against "selected by %" screenshots only |
| G7 | **Rate My Team**: paste an XI → projected percentile vs simulated XIs + best swaps | Instant feedback on your own team | Projections + simulator | M | 5 | differentiator | — |
| G8 | **What-if toggles** (toss winner, dew on/off, pitch type) | Prepare both toss scenarios in advance | Projections conditioned on toss/chase | M | 5 | differentiator | Pitch type has no data source (🔴). Use a venue-par proxy |

### H. Post-match review and accuracy

| # | Feature | User value | Data → Have? | Effort | Phase | Tag | Risk |
|---|---|---|---|---|---|---|---|
| H1 | **Post-match review**: predicted vs actual per player, your XI's rank vs simulated XIs, best-possible C/VC | Learn from each match ~1 h after it ends | Points ✅ (scorer); same-day bbb 🟡 (bcci 0/2,220 ball mismatches) | M | 6 | **must-have** | Waits on post-match harvest. Use provisional points until Cricsheet reconciliation |
| H2 | **Hindsight Dream Team** ("who would've been the best XI") per match and per season, credit-constrained | Fun, shareable, and shows what was achievable | ✅ points; credits 2025 only | S | 6 (can ship 4a for history) | differentiator | 2026 avg unconstrained dream-team = **1,210 pts** (§4 E5). The credit-constrained version needs per-season credits |
| H3 | **Public accuracy / backtest page**: per-season MAE, captain top-2 hit-rate, calibration of ranges | Trust signal (a rival claims 31.4% top-2 captain rate) | Points ✅ + model backtests | M | 7 (baselines can show in 4a) | differentiator | Must be strictly point-in-time (no leakage) |

### I. History, records and fun

| # | Feature | User value | Data → Have? | Effort | Phase | Tag | Risk |
|---|---|---|---|---|---|---|---|
| I1 | **Records & stat explorer**: all-time leaders, partnerships, highest totals, filters by season/venue/phase | Settle any trivia argument | ✅ (§4 E7: Kohli–de Villiers 3,123 partnership runs) | M | 4a | nice-to-have | Scope creep: ship 10 fixed leaderboards first |
| I2 | **Milestones watch**: "Rabada needs 2 for 150 IPL wickets", "Pandya 45 short of 3,000" | Pre-match hooks and captaincy narratives | ✅ (§4 E8) | S | 4a | nice-to-have | Only IPL-career milestones. All-T20 milestones need C4 data |
| I3 | **Streaks & form flags**: consecutive 30+ scores, wicket streaks, fantasy 50+ streaks | Spot hot hands | ✅ | S | 4a | nice-to-have | Hot-hand effect is weak. Present it as information, not a signal |

### J. Personalization

| # | Feature | User value | Data → Have? | Effort | Phase | Tag | Risk |
|---|---|---|---|---|---|---|---|
| J1 | **Saved teams + my history** (local, no accounts; PLAN §6 = personal tool) | Track your own picks and points over the season | own DB table | S–M | 8 | nice-to-have | — |
| J2 | **Notifications**: toss/XI out, re-projection done, your locked player benched, review ready (web push or Telegram bot) | Turns the toss-time data into something you act on in the 30 min before lock | Toss snapshot job 🟡 | M | 8 (pull earlier: 4–5) | must-have | XI timing on sources still untested |
| J3 | **Favourites / watchlist** (teams, players) driving the home feed | Less noise | own table | S | 8 | nice-to-have | — |

---

## 3. What the data cannot support (or only partly)

| Wanted | Why not | Workaround |
|---|---|---|
| Real Dream11 ownership % / "selected by" | No public source; Dream11 shows it only in-app | Proxy model (G6); label it "estimate" |
| Ball tracking (line, length, speed, pitch maps, swing/spin) | No free Hawk-Eye; Ellipse gives shot direction only | Use phase and bowling-type splits |
| Wagon wheels before 2025 | Ellipse `/wagon` is 2025+ | Show only for 2025+ |
| Bowling style / batting hand in the DB | Not stored. Cricsheet `people.csv` has no styles | Cricbuzz series squads (current players) + Cricinfo profiles one-off (retired players) |
| Player role for scoring | Not stored. The scorer needs it for duck/SR rules (this analysis used a bowled ≥12 balls heuristic) | Load iplt20 squad roles per season |
| Day/night and afternoon double-header split, dew analysis | No start time in `match` | Add `start_time` from bcci fixtures; backfill weather via Open-Meteo archive |
| Pitch type (green/dry/flat) | No structured source | Venue par + recent scores as proxy; commentary text mining (low accuracy) |
| Injury news | No reliable structured free feed | Squad replacements in the daily sweep; XI absence |
| Dropped catches, misfields, field placements | Not in Cricsheet/BCCI structured data | Commentary text only; skip |
| 2026 credits; credit-constrained historical dream teams | Only 2025 credits stored | Owner enters credits each season; label 2026 as approximate |
| Cricbuzz identity at scale | Only 50 Cricbuzz IDs mapped | Squad-constrained matcher + overrides (already planned) |

---

## 4. SQL evidence

All run against `postgresql://p11:p11@localhost:5433/p11` on 2026-10-02. Legal ball for a
batter = `coalesce(wides,0)=0`. Bowler wicket = not run out / retired / obstructing.

**E1 Batter vs bowler H2H (D1).** All IPL, super overs excluded.

```sql
select b.name, w.name, count(*) filter (where coalesce(wides,0)=0) balls, sum(batter_runs) runs,
  count(*) filter (where player_out_id=batter_id and wicket_kind not in
    ('run out','retired hurt','retired out','obstructing the field')) dismissals,
  count(distinct match_id) matches
from delivery d join player b on b.id=batter_id join player w on w.id=bowler_id
where not super_over and (batter_id,bowler_id) in (('ba607b88','462411b3'), …) group by 1,2;
```

| Batter | Bowler | Balls | Runs | SR | Outs | 4s+6s | Matches |
|---|---|---|---|---|---|---|---|
| V Kohli | JJ Bumrah | 108 | 159 | 147 | 5 | 22 | 18 |
| RG Sharma | SP Narine | 137 | 145 | 106 | 8 | 18 | 22 |
| MS Dhoni | JJ Bumrah | 65 | 62 | 95 | 4 | 5 | 16 |
| V Kohli | YS Chahal | 54 | 72 | 133 | 2 | 7 | 7 |
| JC Buttler | Rashid Khan | 50 | 30 | 60 | 4 | 0 | 9 |

Sample-size distribution across all 31,370 batter–bowler pairs: median **5 balls**; 7,204 pairs
≥12 balls, 1,615 ≥30, 267 ≥60. This means D1 must show confidence and fall back to D2.

**E2 Venue par and chase bias, 2023–26 (E1).** 1st innings, completed non-DLS wins, ≥10 matches.

| Venue | n | Avg 1st inns | Median | Chase win % |
|---|---|---|---|---|
| Rajiv Gandhi Intl (Hyderabad) | 25 | 197 | 192 | 48 |
| Wankhede | 27 | 197 | 205 | 56 |
| Eden Gardens | 26 | 196 | 199 | 46 |
| Sawai Mansingh | 21 | 195 | 196 | 57 |
| Arun Jaitley | 25 | 194 | 197 | 52 |
| Narendra Modi | 33 | 192 | 199 | 45 |
| M Chinnaswamy | 24 | 190 | 188 | 54 |
| Mullanpur | 17 | 187 | 192 | 53 |
| Ekana (Lucknow) | 26 | 176 | 173.5 | 62 |
| MA Chidambaram | 31 | 173 | 175 | 61 |

**E3 Phase-wise strike rates (C1) and era inflation (E1).** 2022–26:

| Player | Powerplay (1–6) | Middle (7–15) | Death (16–20) |
|---|---|---|---|
| V Kohli | 996 b, SR 151.8 | 928 b, SR 133.3 | 167 b, SR 182.0 |
| MS Dhoni | 5 b, SR 120 | 108 b, SR 66.7 | 350 b, SR 175.7 |

League run rate (per 6 legal balls): powerplay 7.70 (2008) → 7.82 (2022) → 8.72 (2023) → 9.47 → 9.61 → **10.10 (2026)**.
Death 9.95 → 10.79. Toss: 2023–26 teams chose to field 224/288 times; toss winner won 51.8% (field) / 45.3% (bat).

**E4 Points table 2026 (F1)**, recomputed from `match` + `delivery` (NRR from balls; all-out = full quota):

| Team | P | W | L | NR | Pts | NRR |
|---|---|---|---|---|---|---|
| Royal Challengers Bengaluru | 14 | 9 | 5 | 0 | 18 | +0.794 |
| Gujarat Titans | 14 | 9 | 5 | 0 | 18 | +0.695 |
| Sunrisers Hyderabad | 14 | 9 | 5 | 0 | 18 | +0.524 |
| Rajasthan Royals | 14 | 8 | 6 | 0 | 16 | +0.189 |
| Punjab Kings | 14 | 7 | 6 | 1 | 15 | +0.309 |
| Delhi Capitals | 14 | 7 | 7 | 0 | 14 | −0.651 |
| Kolkata Knight Riders | 14 | 6 | 7 | 1 | 13 | −0.147 |
| Chennai Super Kings | 14 | 6 | 8 | 0 | 12 | −0.345 |
| Mumbai Indians | 14 | 4 | 10 | 0 | 8 | −0.584 |
| Lucknow Super Giants | 14 | 4 | 10 | 0 | 8 | −0.751 |

The top 4 matches the actual playoff fixtures in the DB (Q1 RCB v GT, Eliminator RR v SRH; RCB won the final).
NRR still needs the DLS-revised-overs fix before it can be shown as official.

**E4b Playoff scenarios (F2).** State after match 56 of 70, with all 2^14 = 16,384 outcomes of
the remaining 14 games enumerated (50/50, Python, <1 s):

| Team | Pts | Clear top-4 | Top-4 incl. NRR ties |
|---|---|---|---|
| Gujarat Titans | 16 | 87.6% | 99.6% |
| Royal Challengers Bengaluru | 14 | 68.8% | 88.1% |
| Punjab Kings | 13 | 60.9% | 64.5% |
| Sunrisers Hyderabad | 14 | 51.7% | 76.8% |
| Chennai Super Kings | 12 | 29.6% | 53.9% |
| Rajasthan Royals | 12 | 28.1% | 53.8% |
| Kolkata Knight Riders | 9 | 9.2% | 12.8% |
| Delhi Capitals | 10 | 0.1% | 3.2% |
| Mumbai Indians / LSG | 6 | 0% (eliminated) | 0% |

Exhaustive enumeration is instant up to ~20 remaining games. Earlier in the season, switch to Monte Carlo.

**E5 Fantasy points (G2, H2).** Computed with `score_match` for all 2025–26 matches:
- 2026 unconstrained Hindsight Dream Team (top-11 + C×2 + VC×1.5): mean **1,210**, median 1,214, max 1,566.
- Naive captain baseline (highest last-5 mean, ≥3 prior games): top-2 scorer in **7/73 = 9.6%** of 2026 matches, and in the hindsight top-11 46.6% of the time.
- Match top scorer was batting-led in 56 games and bowling-led in 17.

**E6 Consistency leaderboard 2026 (C2):**

| Player | Total | M | Mean | SD | p10–p90 |
|---|---|---|---|---|---|
| V Suryavanshi | 1,610 | 15 | 107.3 | 75.3 | 12–203 |
| Shubman Gill | 1,544 | 16 | 96.5 | 63.5 | 21–168 |
| B Sai Sudharsan | 1,442 | 17 | 84.8 | 57.8 | 24–156 |
| V Kohli | 1,395 | 16 | 87.2 | 53.6 | 10–151 |
| H Klaasen | 1,288 | 15 | 85.9 | **32.0** | **42–121** (most reliable) |

**E7 Partnerships (I1):** Kohli–de Villiers 3,123 runs / 2,053 balls; Gill–Sai Sudharsan 2,966; Kohli–Gayle 2,787.
Kohli venue splits: Chinnaswamy 96 m, 3,448 runs, SR 145.1 vs Chepauk 14 m, SR 110.4.

**E8 Milestones watch (I2)**, active 2026 players: Rabada 148 wkts (2 to 150); Shami and Boult 145; D Chahar 96 (4 to 100);
KH Pandya 1,982 runs (18 to 2,000); T Stubbs 980; HH Pandya 2,955 (45 to 3,000).

**E9 Impact player (B3):** 557 impact in/out pairs (2023: 139, 2024: 137, 2025: 141, 2026: 140). Cold start: 37 of 204 2026 players debuted that season.

---

## 5. Recommended ordering (top 10)

**Step 0 (enabler, S):** persist `player_match_points` (scorer output for all 1,243 matches)
and load player role and styles from squads. Ten features read these. The scorer already runs over
two seasons in seconds.

| Rank | Feature | Why here |
|---|---|---|
| 1 | **F1 Points table** (all seasons) | S effort, 100% on hand. Proven: the recomputed 2026 table reproduces the real top 4. Owner favourite. Also a first end-to-end test of the API → web path |
| 2 | **D1 Batter vs bowler H2H** (+ D3 matchup grid) | Owner favourite. One indexed query, data complete. H2H features also feed the model. Show confidence because pairs are sparse (median 5 balls) |
| 3 | **C1/C2 Player pages + fantasy consistency** | Needed by every other screen (player cards). All data on hand once points are persisted. Floor and ceiling (E6) are what fantasy users want |
| 4 | **E1 Venue & conditions card** (+ E2 dew) | Required for previews and projections. Par scores vary from 173 to 197, which a 2023+ window captures well. E2 is small once start time is scraped |
| 5 | **B1 Team squads** (+ B2 likely XI) | Owner favourite. Off-season is the right time because squads change at the auction. This is also the data path for roles and styles that steps 0, D2 and G1 need |
| 6 | **A1 Match centre** (fixtures → toss → XI → live score) | Owner favourite, and the toss/XI part is the trigger for re-projection. It ranks below 1–5 only because it needs the scrapers live and the "light live poll" decision from the owner. Build it now and test on off-season T20s |
| 7 | **G1 + G2 Projections, optimal XI, captain picker** | The core product. Ranks 1–6 already build its feature store. A 9.6% naive captain baseline gives a clear first target |
| 8 | **H1 + H2 Post-match review + Hindsight Dream Team** | Closes the loop. H2 can ship right after step 0 as a history page, before any model exists |
| 9 | **F2 Playoff scenarios** | Clear differentiator, and the maths is proven (16k scenarios enumerated in <1 s). Matters only from about match 40 onward, so it can follow the core |
| 10 | **H3 Accuracy page** | Trust signal. Baselines (e.g. the 9.6% captain hit-rate) can be published before the model, then the model's improvement is shown against them |

**Next after the top 10:** G3 multi-lineup, G7 Rate My Team, B3 impact intelligence, J2 notifications, D2 bowling-type matchups (after the styles scrape), I2 milestones.
**Defer:** G6 ownership (cannot be validated), A4 live fantasy points (conflicts with the plan's no-live decision), C4 cold start (Phase 7).

**Reasoning summary.** Ranks 1–5 and 8–9 depend on no ML and no new scraping, and they serve
the owner's stated favourites. Their queries become the model's feature inputs, so they shorten
Phase 3 rather than compete with it. With IPL 2027 around late March, the analytics layer (4a)
can be built and used in the off-season on 19 seasons of history. Same-day features (A1, B2, J2)
then get tested on other T20 series before the IPL starts.

## 6. Plan conflicts to resolve

1. **Live score vs PLAN §6 "no live in-match scraping".** A1/A4 need a light live poll of the
   Hindu API. Recommendation: allow status/score polling only (≤1 req/min during matches). Keep
   ball data post-match.
2. **Phase 4a** (analytics pages before the model) is new. It changes the §5 roadmap order but
   not its content.
3. **Data claims to correct:** Cricbuzz IDs (50, not 18.5k). No player role, style or start time
   in the DB. Credits are 2025 only.

## 7. Owner selection (2026-10-02)

**In scope:** A1–A4 (match centre, live score, preview, scorecard charts, live fantasy points),
B1–B4 (squads, likely XI, impact intel, team form), C1–C4 (player pages, leaderboards, compare,
cold start), D1–D4 (H2H, bowling-type splits, matchup grid, team vs team), E1–E2 (venue, dew),
F1–F3 (points table, playoff scenarios, season story), G1–G8 (projections, optimal XI, captain,
multi-lineup, risk slider, why-chips, ownership, Rate My Team, what-if), H1–H3 (review,
hindsight XI, accuracy), I1–I3 (records, milestones, streaks).

**Not now:** J1 saved teams/history, J2 notifications, J3 favourites.

**Decisions this implies:**
- Light **live polling is approved** for the match centre and live fantasy points (A1/A4): a small
  score endpoint every ~1–2 min during matches only (source chosen by the live-score spike).
  Heavy in-match ball-by-ball scraping stays out; post-match harvest remains the source of truth.
- **Step 0 before features:** persist per-match fantasy points; load player role, batting hand,
  bowling style (squads) and match start time — ~10 features depend on them.
