"""Fantasy analytics (no ML): per-player points distributions, season leaderboards, and
hindsight Dream Teams (per match, per season, team of the season).

Data: persisted Dream11 points (p11.analytics.fantasy_data). No-result matches (0 for
everyone) and matches a player did not take part in are excluded from every distribution.
Credits come from ``season_credits`` with the query-time fallback of
p11.registry.credits (2026 uses 2025 credits until 2026 credits are loaded).
"""

from __future__ import annotations

import datetime as dt
import statistics
from collections import Counter
from collections.abc import Sequence
from typing import Literal

from ..optimize.xi import DREAM11, Candidate, Infeasible, Options, Rules, Selection, score, solve
from . import fantasy_data as fd
from .fantasy_schemas import (
    XI,
    CategoryMix,
    Distribution,
    FantasyPlayer,
    FantasyPlayerRef,
    FantasySeasonLine,
    Leaderboard,
    LeaderboardRow,
    MatchBestXI,
    RulesInfo,
    SeasonBestXIs,
    SeasonMatchXI,
    SeasonXI,
    SeasonXIPlayer,
    SparkPoint,
    TeamOfSeason,
    XIPlayer,
)
from .fantasy_stats import Dist, distribution, r1, r2, shares
from .seasons_refs import match_summary, team_ref
from .seasons_schemas import TeamRef

SortKey = Literal["total", "mean", "consistency", "ppc"]
SEASON_XI_RULES = Rules(budget=None, captains=False)
DEFAULT_MIN_MATCHES_MEAN = 7


class NotFound(LookupError):
    pass


# --------------------------------------------------------------------------- helpers
def _pref(d: fd.FantasyData, pid: str) -> FantasyPlayerRef:
    return FantasyPlayerRef(id=pid, name=d.names.get(pid, pid), image_url=d.images.get(pid))


def _team(d: fd.FantasyData, team_id: int, year: int) -> TeamRef:
    return team_ref(d.core, team_id, year)


def _dist_model(x: Dist) -> Distribution:
    return Distribution(
        n=x.n,
        total=x.total,
        mean=round(x.mean, 2),
        median=x.median,
        sd=round(x.sd, 2),
        cv=r2(x.cv),
        p10=round(x.p10, 1),
        p25=round(x.p25, 1),
        p75=round(x.p75, 1),
        p90=round(x.p90, 1),
        floor=round(x.p10, 1),
        ceiling=round(x.p90, 1),
        min=x.min,
        max=x.max,
        pct_50_plus=round(x.pct_50_plus, 1),
        pct_100_plus=round(x.pct_100_plus, 1),
    )


def _mix(rows: Sequence[fd.PointsRow]) -> CategoryMix:
    parts = {
        "batting": sum(r.batting for r in rows),
        "bowling": sum(r.bowling for r in rows),
        "fielding": sum(r.fielding for r in rows),
        "lineup": sum(r.lineup for r in rows),
        "bonuses": sum(r.bonuses for r in rows),
    }
    sh = shares(parts)
    return CategoryMix(
        **parts,
        share_batting=r2(sh["batting"]),
        share_bowling=r2(sh["bowling"]),
        share_fielding=r2(sh["fielding"]),
        share_lineup=r2(sh["lineup"]),
        share_bonuses=r2(sh["bonuses"]),
    )


def _ppc(mean: float, credits: float | None) -> float | None:
    return round(mean / credits, 2) if credits else None


def rules_info(rules: Rules = DREAM11) -> RulesInfo:
    return RulesInfo(
        size=rules.size,
        role_min=dict(rules.role_min),
        role_max=dict(rules.role_max),
        max_per_team=rules.max_per_team,
        budget=rules.budget,
        captain_mult=rules.captain_mult,
        vice_mult=rules.vice_mult,
    )


def latest_season(d: fd.FantasyData) -> int:
    if not d.by_season:
        raise NotFound("no fantasy points loaded")
    return max(d.by_season)


# --------------------------------------------------------------------------- 1. player
def player(
    player_id: str, season: int | None = None, since: dt.date | None = None
) -> FantasyPlayer:
    d = fd.data()
    if player_id not in d.names:
        raise NotFound(f"unknown player {player_id!r}")
    all_rows = d.by_player.get(player_id, [])
    rows = [r for r in all_rows if since is None or r.date >= since]
    sel = [r for r in rows if season is None or r.year == season]
    role = d.role_of(player_id, all_rows)

    lines: list[FantasySeasonLine] = []
    for year in sorted({r.year for r in rows}):
        yr = [r for r in rows if r.year == year]
        x = distribution([r.total for r in yr])
        assert x is not None
        sc = d.credits_for(year)
        cr = sc.credits.get(player_id)
        lines.append(
            FantasySeasonLine(
                season=year,
                team=_team(d, yr[-1].team_id, year),
                role=role,  # type: ignore[arg-type]
                n=x.n,
                total=x.total,
                mean=round(x.mean, 2),
                median=x.median,
                sd=round(x.sd, 2),
                p10=round(x.p10, 1),
                p90=round(x.p90, 1),
                max=x.max,
                credits=cr,
                credits_season=sc.effective if cr is not None else None,
                points_per_credit=_ppc(x.mean, cr),
            )
        )

    dist = distribution([r.total for r in sel])
    cred_line = (
        next((ln for ln in lines if ln.season == season), None)
        if season
        else (lines[-1] if lines else None)
    )
    credits = cred_line.credits if cred_line else None
    last10 = [
        SparkPoint(
            match_id=r.match_id,
            date=r.date,
            season=r.year,
            team=_team(d, r.team_id, r.year),
            opponent=_team(d, d.core.by_id[r.match_id].opponent(r.team_id), r.year),
            points=r.total,
        )
        for r in sel[-10:]
    ]
    return FantasyPlayer(
        player=_pref(d, player_id),
        role=role,  # type: ignore[arg-type]
        season=season,
        since=since,
        distribution=_dist_model(dist) if dist else None,
        category_mix=_mix(sel) if sel else None,
        last10=last10,
        seasons=lines,
        credits=credits,
        credits_season=cred_line.credits_season if cred_line else None,
        points_per_credit=(
            _ppc(dist.mean, credits)
            if dist and cred_line and season is not None
            else (cred_line.points_per_credit if cred_line else None)
        ),
    )


# --------------------------------------------------------------------------- 2. leaderboard
def leaderboard(
    season: int | None = None,
    role: str | None = None,
    min_matches: int = 3,
    sort: SortKey = "total",
    limit: int = 50,
) -> Leaderboard:
    d = fd.data()
    year = season if season is not None else latest_season(d)
    if year not in d.core.seasons:
        raise NotFound(f"no IPL season {year}")
    sc = d.credits_for(year)
    per: dict[str, list[fd.PointsRow]] = {}
    for r in d.by_season.get(year, []):
        per.setdefault(r.player_id, []).append(r)

    out: list[LeaderboardRow] = []
    for pid, prs in per.items():
        if len(prs) < min_matches:
            continue
        prole = d.role_of(pid, d.by_player.get(pid))
        if role is not None and prole != role:
            continue
        x = distribution([r.total for r in prs])
        assert x is not None
        cr = sc.credits.get(pid)
        out.append(
            LeaderboardRow(
                rank=0,
                player=_pref(d, pid),
                team=_team(d, prs[-1].team_id, year),
                role=prole,  # type: ignore[arg-type]
                n=x.n,
                total=x.total,
                mean=round(x.mean, 2),
                median=x.median,
                sd=round(x.sd, 2),
                cv=r2(x.cv),
                p10=round(x.p10, 1),
                p90=round(x.p90, 1),
                max=x.max,
                pct_50_plus=round(x.pct_50_plus, 1),
                credits=cr,
                points_per_credit=_ppc(x.mean, cr),
            )
        )

    def key(r: LeaderboardRow) -> tuple[float, ...]:
        if sort == "mean":
            return (-r.mean, -r.total)
        if sort == "consistency":
            return (r.cv is None, r.cv if r.cv is not None else 0.0, -r.mean)
        if sort == "ppc":
            ppc = r.points_per_credit
            return (ppc is None, -(ppc or 0.0), -r.total)
        return (-r.total, -r.mean)

    out.sort(key=lambda r: (*key(r), r.player.name))
    total_players = len(out)
    with_credits = sum(r.credits is not None for r in out)
    out = out[:limit]
    for i, row in enumerate(out, 1):
        row.rank = i
    return Leaderboard(
        season=year,
        role=role,  # type: ignore[arg-type]
        min_matches=min_matches,
        sort=sort,
        credits_season=sc.effective,
        players_with_credits=with_credits,
        total_players=total_players,
        rows=out,
    )


# --------------------------------------------------------------------------- 4. match best XI
def _xi(
    d: fd.FantasyData,
    sel: Selection,
    year: int,
    actual: dict[str, int],
    objective: float | None = None,
) -> XI:
    players: list[XIPlayer] = []
    counts: Counter[str] = Counter()
    for p in sel.picks:
        c = p.candidate
        team = _team(d, int(c.team), year)  # type: ignore[call-overload]
        counts[team.short_code] += 1
        pts = actual.get(c.player)
        players.append(
            XIPlayer(
                player=_pref(d, c.player),
                team=team,
                role=c.role,  # type: ignore[arg-type]
                multiplier=p.multiplier,
                points=pts,
                scored=None if pts is None else pts * p.multiplier,
                value=round(c.value, 2),
                credits=c.credits,
            )
        )
    total = sum(p.scored or 0.0 for p in players)
    return XI(
        players=players,
        captain=sel.captain,
        vice_captain=sel.vice_captain,
        total=total,
        base_total=float(sum(p.points or 0 for p in players)),
        objective=round(objective if objective is not None else sel.total, 2),
        credits_used=sel.credits_used,
        credits_constrained=sel.credits_constrained,
        team_counts=dict(counts),
        solver=sel.solver,
    )


class _MatchXIs:
    __slots__ = ("best", "best_credits", "naive", "naive_total", "missing", "actual", "eff")

    def __init__(self) -> None:
        self.best: Selection | None = None
        self.best_credits: Selection | None = None
        self.naive: Selection | None = None
        self.naive_total: float | None = None
        self.missing: list[str] = []
        self.actual: dict[str, int] = {}
        self.eff: int | None = None


def _solve_match(match_id: int) -> _MatchXIs:
    def compute() -> _MatchXIs:
        d = fd.data()
        m = d.match(match_id)
        out = _MatchXIs()
        if m is None or m.result == "no_result":
            return out
        rows = d.by_match.get(match_id, [])
        sc = d.credits_for(m.year)
        out.eff = sc.effective
        out.actual = {r.player_id: r.total for r in rows}
        pool = [
            Candidate(r.player_id, r.team_id, r.role, float(r.total), sc.credits.get(r.player_id))
            for r in rows
        ]
        try:
            out.best = solve(pool, options=Options(use_credits=False))
        except Infeasible:
            return out
        if sc.effective is not None:
            priced = [c for c in pool if c.credits is not None]
            out.missing = sorted(c.player for c in pool if c.credits is None)
            try:
                out.best_credits = solve(priced)
            except Infeasible:
                out.best_credits = None
        seq = d.seq[match_id]
        form_pool = [
            Candidate(c.player, c.team, c.role, d.form(c.player, seq) or 0.0, c.credits)
            for c in pool
        ]
        try:
            out.naive = solve(form_pool, options=Options(use_credits=False))
            actual_pool = [
                Candidate(
                    p.candidate.player,
                    p.candidate.team,
                    p.candidate.role,
                    float(out.actual[p.candidate.player]),
                )
                for p in out.naive.picks
            ]
            out.naive_total = score(actual_pool, out.naive.captain, out.naive.vice_captain)
        except Infeasible:
            out.naive = None
        return out

    return fd.memo(f"match-xi:{match_id}", compute)


def match_best_xi(match_id: int) -> MatchBestXI:
    d = fd.data()
    m = d.match(match_id)
    if m is None:
        raise NotFound(f"no IPL match {match_id}")
    r = _solve_match(match_id)
    best = _xi(d, r.best, m.year, r.actual) if r.best else None
    naive = _xi(d, r.naive, m.year, r.actual) if r.naive else None
    return MatchBestXI(
        match=match_summary(d.core, m),
        no_result=m.result == "no_result",
        rules=rules_info(),
        credits_season=r.eff,
        best=best,
        best_with_credits=_xi(d, r.best_credits, m.year, r.actual) if r.best_credits else None,
        without_credits=[_pref(d, p) for p in r.missing],
        naive_form=naive,
        gap=round(best.total - naive.total, 1) if best and naive else None,
    )


# --------------------------------------------------------------------------- 5. team of season
def _season_pool(d: fd.FantasyData, year: int) -> dict[str, list[fd.PointsRow]]:
    per: dict[str, list[fd.PointsRow]] = {}
    for r in d.by_season.get(year, []):
        per.setdefault(r.player_id, []).append(r)
    return per


def _season_xi(
    d: fd.FantasyData,
    year: int,
    per: dict[str, list[fd.PointsRow]],
    metric: Literal["total", "mean"],
    min_matches: int,
) -> SeasonXI:
    pool = []
    for pid, prs in per.items():
        if len(prs) < min_matches:
            continue
        tot = sum(r.total for r in prs)
        val = float(tot) if metric == "total" else tot / len(prs)
        pool.append(Candidate(pid, prs[-1].team_id, d.role_of(pid, d.by_player.get(pid)), val))
    sel = solve(pool, SEASON_XI_RULES)
    players = []
    for p in sel.picks:
        prs = per[p.candidate.player]
        tot = sum(r.total for r in prs)
        players.append(
            SeasonXIPlayer(
                player=_pref(d, p.candidate.player),
                team=_team(d, int(p.candidate.team), year),  # type: ignore[call-overload]
                role=p.candidate.role,  # type: ignore[arg-type]
                matches=len(prs),
                total=tot,
                mean=round(tot / len(prs), 2),
            )
        )
    return SeasonXI(
        metric=metric,
        min_matches=min_matches,
        players=players,
        sum_total=sum(p.total for p in players),
        sum_mean=round(sum(p.mean for p in players), 2),
        solver=sel.solver,
    )


def team_of_season(year: int, min_matches: int = DEFAULT_MIN_MATCHES_MEAN) -> TeamOfSeason:
    def compute() -> TeamOfSeason:
        d = fd.data()
        per = _season_pool(d, year)
        if not per:
            raise NotFound(f"no fantasy points for season {year}")
        try:
            by_mean = _season_xi(d, year, per, "mean", min_matches)
        except Infeasible as e:
            raise ValueError(f"no valid XI with min_matches={min_matches}: {e}") from e
        return TeamOfSeason(
            season=year,
            rules=rules_info(SEASON_XI_RULES),
            by_total=_season_xi(d, year, per, "total", 1),
            by_mean=by_mean,
        )

    return fd.memo(f"tos:{year}:{min_matches}", compute)


# --------------------------------------------------------------------------- 6. season best XIs
def season_best_xis(year: int) -> SeasonBestXIs:
    def compute() -> SeasonBestXIs:
        d = fd.data()
        matches = d.core.season_matches(year)
        if not matches or year not in d.by_season:
            raise NotFound(f"no fantasy points for season {year}")
        out: list[SeasonMatchXI] = []
        nr: list[int] = []
        for m in matches:
            if m.result == "no_result":
                nr.append(m.id)
                continue
            r = _solve_match(m.id)
            if r.best is None or r.naive is None or r.naive_total is None:
                continue
            top = max(d.by_match[m.id], key=lambda x: (x.total, x.player_id))
            out.append(
                SeasonMatchXI(
                    match_id=m.id,
                    date=m.date,
                    match_number=m.match_number,
                    stage=m.stage,
                    team1=_team(d, m.team1_id, year),
                    team2=_team(d, m.team2_id, year),
                    best_total=r.best.total,
                    naive_total=r.naive_total,
                    gap=r.best.total - r.naive_total,
                    best_with_credits_total=r.best_credits.total if r.best_credits else None,
                    captain=_pref(d, r.best.captain or ""),
                    top_scorer=_pref(d, top.player_id),
                    top_points=top.total,
                )
            )
        bests = [x.best_total for x in out]
        return SeasonBestXIs(
            season=year,
            credits_season=d.credits_for(year).effective,
            matches=out,
            no_result_matches=nr,
            mean_best=r1(statistics.fmean(bests)) if bests else None,
            median_best=r1(statistics.median(bests)) if bests else None,
            max_best=max(bests) if bests else None,
            mean_naive=r1(statistics.fmean(x.naive_total for x in out)) if out else None,
            mean_gap=r1(statistics.fmean(x.gap for x in out)) if out else None,
        )

    return fd.memo(f"season-xis:{year}", compute)
