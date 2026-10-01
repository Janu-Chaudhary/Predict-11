# Scraping spike results (2026-10-01)

Real probes against live sites using IPL 2026 matches, off-season. Scripts + raw payloads are in
`spikes/<source>/` (payloads are gitignored). Test matches: Final (GT v RCB), a league match,
#38 KKR v LSG (tie + super over), #50 LSG v RCB (DLS).

## Verdict per source

| | Cricsheet | iplt20 / stats.bcci.tv | ESPNcricinfo + ESPN API | Cricbuzz |
|---|---|---|---|---|
| Access | open zips | plain HTTP (`Edak` header for ball-by-ball) | curl_cffi for pages; plain requests for ESPN API | plain requests |
| Browser needed | no | no (only to re-capture key) | no (headless works only with full chromium + UA override; fragile) | no |
| Same day | ❌ median 1 d, max 6 d | ✅ | ✅ | ✅ |
| Toss + XI | ✅ | ✅ official | ✅ | ✅ |
| Impact sub + timing | ✅ `replacements` | ✅ over + time | ✅ over + innings | ⚠️ in/out flag; timing only in prose |
| Ball-by-ball | ✅ incl. non-striker | ✅ names only (no IDs/ball) | ✅ structured, 25/page, 502s need retry | ✅ via commentary + text parsing |
| Super over balls | ✅ | not checked | scorecard ✅ / API ❌ | ❌ prose only |
| Fielders | ✅ | ✅ | ✅ scorecard (API run-outs empty) | ✅ scorecard IDs |
| Squads + overseas | ❌ | ✅ official, 274 players | ✅ | ✅ |
| **Player ID → Cricsheet** | native | ❌ new IDs; 161/274 exact short-name match | ✅ **exact** via `key_cricinfo` (202/202) | ❌ 3/202; name matcher |
| Validated vs scorecard / Cricsheet | — | ✅ final + M70 exact | ✅ 4 matches, 0 run/wkt mismatches vs Cricsheet | ✅ 4 matches exact; non-striker reconstruction 0/950 mismatches |
| Main risk | lag | `Edak` key rotation; robots disallow | domain moves (espncricinfo→cricinfo), API 502s | text-format changes |

## Endpoints that worked

- **Cricsheet**: `downloads/ipl_json.zip`, `recently_added_{2,7,30}_json.zip`, `register/people.csv`, `register/names.csv`
- **iplt20**: season gid `iplt20.com/api/bff/cms/matches?status=results&season=YYYY` →
  `stats.bcci.tv/match/{results,fixtures}/?comp_gid=…` → `stats.bcci.tv/match/<uuid>/scorecard`;
  ball-by-ball `epr.ellipsedata.com/redirect/1/match/<uuid>/commentary` (header `Edak`);
  squads `iplt20.com/api/bff/cms/teams/<slug>?tab=squad`, `epr…/comp/<compId>/squads?team_id=`
- **ESPNcricinfo**: `cricinfo.com/series/ipl-2026-1510719/<slug>-<id>/full-scorecard` →
  `__NEXT_DATA__` (curl_cffi, impersonate=chrome); ESPN API
  `site.web.api.espn.com/apis/site/v2/sports/cricket/8676/playbyplay?event=<id>&page=N`
- **Cricbuzz**: `/api/mcenter/scorecard/<mid>`, `/api/mcenter/<mid>/full-commentary/<inn>`,
  `/cricket-match-squads/<mid>/match` (Next.js flight data), `/api/cricket-series/series-squads/<sid>/<squadId>`
- **Open-Meteo**: archive + forecast APIs, hourly temp / RH / dew point, no key
- **CricketData.org**: needs free API key (owner signup) — not tested beyond that

## Surprises (things the plan had wrong)
1. Cricsheet is **complete for 2026 (74/74)**, but the current format is **JSON 1.2**, not the YAML
   the old parser reads — the old parser would silently load zero deliveries.
2. The local `data/raw/cricsheet_ipl` copy stops partway into 2025; `data/raw/Teams/*.csv` are 2025 squads.
3. The official IPL data comes via **stats.bcci.tv + CricViz/Ellipse**, and it's the richest same-day
   source (official XIs, impact-sub timing).
4. ESPNcricinfo moved its API to `hs-consumer-api.cricinfo.com` with per-URL HMAC tokens; we
   avoid it entirely by using `__NEXT_DATA__` + the open ESPN API (no token forging).
5. Headless Chrome is **detected by default** on Cricinfo; only full chromium + UA override passes,
   and UI-driving lost balls on one match → browsers are fallback only.
6. Every same-day source names players differently ("Virat Kohli", "V Kohli", "B Sai Sudharsan",
   "N Sindhu") → **join only on IDs**; ESPN is the ID bridge.
7. Matching scraped matches to Cricsheet by date alone fails on double-headers → date + both teams.
8. Non-striker isn't given by Cricbuzz but is reconstructable exactly (0 mismatches in 4 matches).
9. DLS target is only in status text on Cricbuzz/ESPN; super-over balls are missing on Cricbuzz and the ESPN API.

## Resulting source strategy (updated after 10-match validation)

| Need | Primary | Secondary | Tertiary |
|---|---|---|---|
| Fixtures / results | stats.bcci.tv | Cricinfo series page | Cricbuzz series page |
| Toss + XI + impact subs (T-35 min) | stats.bcci.tv scorecard | Cricinfo `__NEXT_DATA__` | Cricbuzz squads page |
| Ball-by-ball (post-match) | stats.bcci.tv `/bbb` | ESPN API (IDs = Cricsheet) | Cricbuzz commentary |
| Scorecard + fielders | stats.bcci.tv | Cricinfo `__NEXT_DATA__` | Cricbuzz |
| Squads + overseas | iplt20 official | Cricinfo match-squads | Cricbuzz |
| Player ID bridge | Cricinfo objectId = `key_cricinfo` | name matcher (squad-constrained) | `overrides.csv` |
| History + truth | Cricsheet JSON (2008→, all T20 for cold start) | — | — |
| Weather / dew | Open-Meteo | — | — |

Rule: every match is cross-checked across ≥2 same-day sources (innings totals, wickets, per-player
runs/wkts); Cricsheet overwrites when it lands and the delta is logged as scraper accuracy.

## 10-match validation (2026-10-02)

Matches: M1, M12 (no result), M28, M38 (tie + super over), M50 (DLS), M70, Q1, Eliminator, Q2,
Final. Each source → normalized JSON → `spikes/compare/compare.py` vs Cricsheet (toss, XI,
innings totals, per-player runs/balls/wkts/catches, every ball: batter, bowler, non-striker,
player_out, extra type, wicket kind, runs, extras, fielders). Re-verified independently.

| Source | Toss | XI | Innings | Player stats | Ball mismatches | Identity | Cost / match |
|---|---|---|---|---|---|---|---|
| **stats.bcci.tv** (`/match/<uuid>/scorecard` + `/bbb?size=500`) | 10/10 | 10/10 | 10/10 | 0 | **0 / 2,220** | BCCI IDs + 3-entry crosswalk | 2–3 req, ~7 s |
| **ESPN** (`__NEXT_DATA__` + open playbyplay API) | 10/10 | 10/10 | 10/10 | 0 | **0** | **cricinfo ID, 239/239 exact** | ~11 req, ~11 s |
| **Cricbuzz** (mcenter JSON + commentary) | 10/10 | 10/10* | 10/10 | 0* | 1 (byes vs leg-byes, source dispute) + 4 super-over non-strikers | name matcher + 4 overrides | 4 req, ~4 s |

\* after `spikes/compare/overrides.json` (CV Varun, V Suryavanshi, Rasikh Salam, R Smaran);
without it 8/10 XIs fail — all mismatches were identity, none were scraping errors.

**Final source roles**
1. **stats.bcci.tv = primary** for XI/toss/impact subs and ball-by-ball (official, one request
   for every ball, includes non-striker and player IDs, no key needed for core data).
2. **ESPN open route = identity bridge + secondary** (cricinfo IDs = Cricsheet `key_cricinfo`);
   use it to map BCCI/Cricbuzz IDs → Cricsheet IDs automatically per match (same match, same
   22 players → join by team + scorecard position/runs), removing most manual crosswalk work.
3. **Cricbuzz = tertiary** cross-check / fallback.
4. **Cricsheet** = training history + final truth.

**Issues found and handled during validation**
- BCCI feed has wrong short names (Riyan Parag → "RP Das", Eshan Malinga → "KKEM Dharmasena");
  BCCI super-over innings numbered 5/6; retired-hurt-and-returned must not be a wicket.
- ESPN API: intermittent 502/504 (recovered by backoff; 10 retries in 123 requests on the first
  run, 0 on a re-run); no super-over balls (rebuilt from scorecard aggregates only when exactly one ball order fits; fragile, prefer BCCI);
  empty placeholder row on no-result matches.
- Cricbuzz: wicket on a wide filed under previous ball; "1 leg bye" / "hit wkt" text variants;
  super over only in prose.
- The checker itself had weak toss/ball checks. These were fixed and all three sources re-scored.

## Full-season run, IPL 2026, 74 matches (2026-10-02, re-verified)

| Source | Toss | XI | Innings | Player-stat mismatch matches | Ball-field diffs | Cost |
|---|---|---|---|---|---|---|
| stats.bcci.tv | 74/74 | 74/74 | 74/74 | 2 | 11 in 5 matches (of 17,527 balls) | ~160 req full season, 0 errors |
| Cricbuzz (6 overrides) | 74/74 | 74/74 | 73/74 | 2 | ~17 in 8 matches | 295 req / 5.5 min, 0 errors |
| ESPN | pending | | | | | |

All 74 matches map 1:1 by date + both teams on both sources.

**Cricsheet is not always right.** In 1527679 (catch: Kishan vs c&b), 1527678 (Pant run-out
fielder missing) and 1527687 (incoming batter after a run-out), BCCI **and** Cricbuzz agree with
each other against Cricsheet. → Merge policy changed: **per-field majority vote across sources
(Cricsheet = one vote, tie-break priority BCCI > Cricsheet > ESPN > Cricbuzz), disagreements kept
with evidence and flagged** — not "Cricsheet overwrites".

Other source-level quirks found: Cricbuzz commentary can miss a delivery its own scorecard counts
(1527691 wide); BCCI attaches retirements to the next ball; BCCI initials-style names collide
(K Sharma) → prefer full-name resolution; run-out credit differs between sources (direct hit vs
involvement) → matters for Dream11 run-out points.

## Still untested
- How early the XI appears on each site before a live match (off-season now) → test on the next
  live T20 (any series) before IPL 2027.
- Retired-hurt batters in non-striker reconstruction.
- `Edak` key rotation frequency; CricketData.org (needs key).
