# Dream11 T20 / IPL fantasy points: researched rules

Researched 2026-10-02. These rules are encoded in `rules.py` (`T20_2024`, `T20_2025`, `T20_2026`)
and applied by `scorer.py`.

## Sources

| # | Source | What it showed |
|---|--------|----------------|
| S1 | Official page `https://www.dream11.com/fantasy-cricket/point-system`, Wayback snapshots **2025-04-23** and **2026-01-17** (`web.archive.org/web/<ts>id_/...`) | The current T20 table. The page returned HTTP 502 when fetched live on 2026-10-02. |
| S2 | Official page `https://www.dream11.com/games/fantasy-cricket/how-to-play`, **fetched live 2026-10-02** | The same T20 values as S1, plus the "Other important points" and the substitute rules |
| S3 | S1 snapshots **2024-02-27, 2024-06-18, 2024-09-19, 2025-01-13** | The previous T20 system (`T20_2024`) |
| S4 | `https://www.dream11.com/games/point-system`, snapshot **2025-02-09** | An intermediate version: the new batting table and dot balls with wicket still at +25 |
| S5 | Static Dream11 page `https://d13ir53smqqeyp.cloudfront.net/d11-static-pages/point-system.html` (2019) | An older rule that super-over events don't count. S2 still states this rule today. |
| S6 | Secondary sources: cricjosh.in/blog/dream11-points-system-explained-2026, toolsly.in/cricket-fantasy-points, ipl-betting-cricket.us.com/dream11-point-calculation, blitzpools.com/dream11-point-calculation | Mostly out of date: they mix old IPL-tab values with new T20 values. Used only as hints. |

**IPL uses the T20 table.** Up to early 2024 the official page had a separate "TATA IPL" tab: boundary +1, six +2, wicket +25, 4w +8, 5w +16 and maiden +8. That tab was removed from the navigation by 2025-04-23 (S1). Its markup is still in the HTML, but it is hidden or commented out. Several secondary sites still quote it, and they are wrong.

## Rule table

✅ = verified verbatim on an official page. ⚠️ = **unverified**: our interpretation or an inferred value.

| Rule | T20_2025 / T20_2026 (current) | T20_2024 (legacy) | Status |
|---|---|---|---|
| In announced lineups (starting XI) | +4 | +4 | ✅ S1/S2 |
| Playing substitute (Impact Player, concussion, X-Factor, full-time replacement) **who plays** | +4 (announced but unused: 0) | +4 | ✅ S2 (legacy ⚠️) |
| Announced in XI but unable to start | 0 for everything. The replacement gets the points. | same | ✅ S2 |
| Other substitutes (ordinary sub fielders) | 0 for any contribution | same | ✅ S2 |
| Run | +1 | +1 | ✅ |
| Boundary bonus | +4 | +1 | ✅ |
| Six bonus | +6 | +2 | ✅ |
| Overthrow that reaches the boundary | Runs count, but no boundary bonus | same | ✅ S1 (supply `is_boundary=False`) |
| Run milestones | 25: +4, 50: +8, 75: +12, 100: +16 | 30: +4, 50: +8, 100: +16 | ✅ values |
| Milestone stacking | A century pays **only** the century bonus | same | ✅ S2 |
| Milestones below 100 | **Highest milestone only** (default `HIGHEST_ONLY`). `STACK_BELOW_CENTURY` is also available. | same | ⚠️ see note 1 |
| Duck (dismissed for 0) | −2, **Batter, WK and All-Rounder only** (bowlers exempt) | −2 | ✅ |
| Strike rate (min 10 balls, **not Bowlers**) | >170: +6; 150.01–170: +4; 130–150: +2; 60–70: −2; 50–59.99: −4; <50: −6 | same | ✅ |
| Dot ball | +1 per dot. **Byes and leg-byes count as dots** for the bowler. Wides and no-balls are never dots. | — (none) | ✅ S2 |
| Wicket (excluding run out) | +30 | +25 | ✅ |
| LBW / bowled bonus | +8 | +8 | ✅ |
| 3 / 4 / 5 wicket bonus | +4 / +8 / +12, highest only (default). `STACK` is also available. | +4 / +8 / +16 | ✅ values, ⚠️ stacking (note 1) |
| Maiden over | +12 | +12 | ✅ value, ⚠️ definition (note 3) |
| Economy (min 2 overs) | <5: +6; 5–5.99: +4; 6–7: +2; 10–11: −2; 11.01–12: −4; >12: −6 | same | ✅ |
| Catch | +8 | +8 | ✅ |
| 3-catch bonus | +4, paid **once** (6 catches still gets +4) | same | ✅ |
| Caught and bowled | The bowler gets the wicket **and** the catch | same | ⚠️ standard practice, not stated on the page |
| Stumping | +12 | +12 | ✅ |
| Run out, direct hit (the only fielder to touch the ball) | +12 | +12 | ✅ |
| Run out, not a direct hit | +6 each to the **last 2** fielders who touched the ball | +6 | ✅ |
| Captain / vice-captain | 2× / 1.5× | same | ✅ |
| Super over / Super Five | **No points** for anything that happens in it | same | ✅ S2, S5 |
| Effective date | 2025: 2025-03-22. 2026: 2026-01-01. | ≤2024-02-27 to 2025-03-21 | ⚠️ see note 4 |

## Notes and decisions

1. **Milestone and haul stacking: verified highest-only (2026-10-02).** Our scorer was checked against 40 published IPL 2026 season-to-date Dream11 totals (khelnow.com "Top 5 Dream11 fantasy picks" articles, e.g. https://khelnow.com/cricket/rcb-vs-gt-top-dream11-fantasy-picks-ipl-202605; 49 innings of 50–74, 22 of 75–99, a 4-wicket and a 5-wicket haul) and matched all 40 exactly. Stacking breaks ~30 of them (Gill 1570 vs 1522). The same check confirmed: caught-and-bowled also earns the +8 catch (Rabada, Narine), byes/leg-byes count as dot balls, super overs score nothing, Impact Player +4, and **no-result matches score 0 for everyone** (`score_match(..., no_result=True)`). Caveat: khelnow does not name its data source; its numbers fit Dream11's rules and no other scheme tested. Script: `spikes/scoring_check/check_totals.py`.
2. **Bowler runs conceded** = batter runs + wides + no-ball extras. Byes, leg-byes and penalty runs are not charged to the bowler (Laws of Cricket). These are the runs used for economy and maidens. A ball with mixed extras (no-ball plus byes) can pass `extras_detail`. Without it, all of a no-ball's extras are charged to the bowler.
3. **Maiden** = one bowler bowls all 6 legal balls of an over (same innings and over) and concedes 0 runs (definition in note 2). A wide or no-ball spoils the maiden. Byes and leg-byes do not. The page describes a maiden only as "An over in which no runs are scored" and does not say how byes are treated. We follow the cricket convention, so this is ⚠️. A partial over (innings ended, or the bowler was injured mid-over) never counts as a maiden.
4. **Effective dates (approximate).** The batting table and dot balls changed between 2025-01-13 and 2025-02-09 (S3 vs S4). The wicket value went from +25 to +30 between 2025-02-09 and 2025-04-23 (the how-to page marks +30 as "New"). We use the IPL 2025 opening day, 2025-03-22. We did not model the short Feb–Mar 2025 hybrid as its own version. We found **no change for 2026**: the 2026-01-17 snapshot and the live page on 2026-10-02 are identical to 2025. `T20_2026` is a separate version with the same values, so any future change only needs a new `RuleSet`. The start date of the legacy set is not known; it was confirmed live on 2024-02-27.
5. **Balls faced** include no-balls but not wides. The strike-rate minimum (10) is checked against balls faced, and SR = 100·runs/balls. Bands are compared as exact fractions. Edge values: exactly 170 gets +4, exactly 150 gets +2, exactly 70 gets −2, and 59.99 gets −4.
6. **Economy minimum** = 12 legal balls. Economy = 6·conceded/legal balls, compared exactly. Exactly 7.00 gets +2, 10.00 gets −2, 11.00 gets −2, and 12.00 gets −4.
7. **Retired hurt / retired not out** are not dismissals: no duck and no bowler wicket. Balls and runs still count. **Retired out**, **obstructing the field** and **timed out** are dismissals (a duck applies) but are not bowler wickets. ⚠️ Dream11 doesn't address retirements; we follow the cricket scorecard convention.
8. **Run-out data.** `Delivery.runout_direct` can be given explicitly. If it is `None`, one listed fielder is treated as a direct hit and two or more as not direct, with the last two in source order scoring +6. Cricsheet lists the thrower first and the keeper or bowler second. A source that lists only the thrower for an assisted run-out will be over-credited as a direct hit (⚠️ a data limitation).
9. **Impact Player.** The player who is substituted out keeps their +4 and everything they did before (and after, if they return). The player who comes in gets +4 plus their contributions. An announced substitute who doesn't play gets 0. If the data shows a supposedly unused substitute taking part, they are promoted to "played" and a warning is recorded.
10. **"Batting more than once in an innings"** (best knock only) applies only to warm-up matches. We ignore it: a batter's runs are aggregated over the match.
11. Not modelled: The Hundred, T10, OD and Test formats, the "Other T20" tables, and Dream11's 2nd-innings contest format (no lineup points). Points for multiple wickets on a single delivery (very rare) cover only the first wicket recorded.
