"""Season story (F3): orange/purple cap races and season leaderboards (all stages)."""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from .seasons_data import BatRow, BowlRow, Core, MatchRow, PlayerData
from .seasons_nrr import balls_to_overs
from .seasons_refs import player_ref, team_ref
from .seasons_schemas import (
    BattingLeader,
    BowlingLeader,
    CapRace,
    RaceSeries,
    SeasonStory,
    TeamRef,
)

TOP_N = 5


@dataclass
class _Bat:
    innings: int = 0
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    teams: Counter[int] = field(default_factory=Counter)


@dataclass
class _Bowl:
    innings: int = 0
    balls: int = 0
    runs: int = 0
    wickets: int = 0
    teams: Counter[int] = field(default_factory=Counter)


def cumulative_race(
    events: Sequence[tuple[dt.date, str, int]], players: Sequence[str]
) -> tuple[list[dt.date], dict[str, list[int]]]:
    """Running totals per date for ``players`` from (date, player, amount) events."""
    dates = sorted({d for d, _, _ in events})
    per: dict[str, dict[dt.date, int]] = defaultdict(lambda: defaultdict(int))
    for d, p, v in events:
        per[p][d] += v
    series: dict[str, list[int]] = {}
    for p in players:
        run, out = 0, []
        for d in dates:
            run += per[p].get(d, 0)
            out.append(run)
        series[p] = out
    return dates, series


def build_story(
    core: Core,
    pdata: PlayerData,
    year: int,
    matches: Sequence[MatchRow],
    *,
    min_balls: int,
    min_overs: int,
) -> SeasonStory:
    date_of = {m.id: m.date for m in matches}
    bat_rows: list[BatRow] = [b for b in pdata.batting if b.match_id in date_of]
    bowl_rows: list[BowlRow] = [b for b in pdata.bowling if b.match_id in date_of]
    bats: dict[str, _Bat] = defaultdict(_Bat)
    for b in bat_rows:
        a = bats[b.player_id]
        a.innings += 1
        a.runs += b.runs
        a.balls += b.balls
        a.fours += b.fours
        a.sixes += b.sixes
        a.teams[b.team_id] += 1
    bowls: dict[str, _Bowl] = defaultdict(_Bowl)
    for w in bowl_rows:
        o = bowls[w.player_id]
        o.innings += 1
        o.balls += w.balls
        o.runs += w.runs
        o.wickets += w.wickets
        o.teams[w.team_id] += 1

    def tref(teams: Counter[int]) -> TeamRef | None:
        return team_ref(core, teams.most_common(1)[0][0], year) if teams else None

    def sr(a: _Bat) -> float:
        return round(100 * a.runs / a.balls, 2) if a.balls else 0.0

    def econ(o: _Bowl) -> float:
        return round(6 * o.runs / o.balls, 2) if o.balls else 0.0

    def bat_leader(pid: str) -> BattingLeader:
        a = bats[pid]
        return BattingLeader(
            player=player_ref(pdata, pid),
            team=tref(a.teams),
            innings=a.innings,
            runs=a.runs,
            balls=a.balls,
            strike_rate=sr(a),
            fours=a.fours,
            sixes=a.sixes,
        )

    def bowl_leader(pid: str) -> BowlingLeader:
        o = bowls[pid]
        return BowlingLeader(
            player=player_ref(pdata, pid),
            team=tref(o.teams),
            innings=o.innings,
            overs=balls_to_overs(o.balls),
            runs=o.runs,
            wickets=o.wickets,
            economy=econ(o),
        )

    orange = sorted(bats, key=lambda p: (-bats[p].runs, -sr(bats[p]), p))[:TOP_N]
    purple = sorted(bowls, key=lambda p: (-bowls[p].wickets, econ(bowls[p]), p))[:TOP_N]
    o_dates, o_series = cumulative_race(
        [(date_of[b.match_id], b.player_id, b.runs) for b in bat_rows], orange
    )
    p_dates, p_series = cumulative_race(
        [(date_of[w.match_id], w.player_id, w.wickets) for w in bowl_rows], purple
    )
    sixes = sorted(bats, key=lambda p: (-bats[p].sixes, -bats[p].runs, p))[:TOP_N]
    sr_ok = [p for p in bats if bats[p].balls >= min_balls]
    best_sr = sorted(sr_ok, key=lambda p: (-sr(bats[p]), -bats[p].runs, p))[:TOP_N]
    ec_ok = [p for p in bowls if bowls[p].balls >= min_overs * 6]
    best_ec = sorted(ec_ok, key=lambda p: (econ(bowls[p]), -bowls[p].balls, p))[:TOP_N]

    return SeasonStory(
        season=year,
        orange_cap=CapRace(
            dates=o_dates,
            leaders=[
                RaceSeries(
                    player=player_ref(pdata, p),
                    team=tref(bats[p].teams),
                    total=bats[p].runs,
                    cumulative=o_series[p],
                )
                for p in orange
            ],
        ),
        purple_cap=CapRace(
            dates=p_dates,
            leaders=[
                RaceSeries(
                    player=player_ref(pdata, p),
                    team=tref(bowls[p].teams),
                    total=bowls[p].wickets,
                    cumulative=p_series[p],
                )
                for p in purple
            ],
        ),
        most_sixes=[bat_leader(p) for p in sixes],
        best_strike_rate=[bat_leader(p) for p in best_sr],
        best_economy=[bowl_leader(p) for p in best_ec],
        min_balls_for_strike_rate=min_balls,
        min_overs_for_economy=min_overs,
    )
