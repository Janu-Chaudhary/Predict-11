"""Predicted XIs per played match, from the honest out-of-sample predictions of a model run.

Only rows the training pipeline predicted *before* each match are used:

- ``walkforward`` (the latest season, 2026): models retrained every ``wf_block`` matches on
  earlier matches only, then used to predict the next block.
- ``test`` (2025, optional): one frozen model trained on seasons before 2025, never retrained.

The final serving booster (trained on everything, 2026 included) is never used here: predicting
2026 with it would leak the answers. The XIs come from the same optimiser as the Model Lab
(``model_lab.solve_xi``: Dream11 roles/team rules, C x2 / VC x1.5, *no* credit cap), picked on
the predicted mean (model), the last-5 average (baseline) or the actual points (best possible),
and every XI is scored with the actual points.

Results are cached per run version + eval-frame/telemetry file stamp (``model_lab._cached``).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, Field

from . import model_lab as ml
from .seasons_schemas import InningsScore, VenueRef

log = logging.getLogger(__name__)

PHASES = ("walkforward", "test")
METHOD_NOTE = "Predicted before the match using only earlier matches (walk-forward)."
FROZEN_NOTE = (
    "Predicted before the match by one frozen model trained on earlier seasons only "
    "(not retrained during the season)."
)
CREDITS_NOTE = (
    "XIs are chosen without the 100-credit cap (Dream11 role limits and max 10 per team apply); "
    "the credits shown are what the picks would cost, using {season} credits."
)


# --------------------------------------------------------------------------- schemas
class TeamSide(BaseModel):
    id: int | str | None = None
    name: str
    short_code: str


class MatchHeader(BaseModel):
    match_id: int
    date: str | None = None
    season: int | None = None
    match_number: int | None = None
    stage: str | None = None
    title: str
    team1: TeamSide | None = None
    team2: TeamSide | None = None
    venue: VenueRef | None = None
    venue_name: str | None = None
    city: str | None = None
    winner_id: int | None = None
    result_text: str | None = None
    scores: list[InningsScore] = Field(default_factory=list)


class PlayerLite(BaseModel):
    id: str
    name: str
    image_url: str | None = None
    team: str
    role: str


class CaptainCall(BaseModel):
    player: PlayerLite
    predicted: float | None  # model mean that made it captain
    actual: float | None  # actual fantasy points (before x2)
    points: float | None  # actual x2
    actual_rank: int | None  # 1 = top scorer of the match
    top2: bool | None


class SeasonMatch(BaseModel):
    match: MatchHeader
    n_players: int
    model_xi_points: float | None
    baseline_xi_points: float | None
    best_xi_points: float | None
    model_minus_baseline: float | None
    model_beat_baseline: bool | None
    captain: CaptainCall | None
    baseline_captain_top2: bool | None
    mae_model: float | None = None
    mae_base: float | None = None
    coverage: float | None = None


class CallRef(BaseModel):
    match_id: int
    title: str
    margin: float  # model XI - baseline XI (actual points)


class SeasonStats(BaseModel):
    matches: int
    model_total: float | None
    model_mean: float | None
    baseline_total: float | None
    baseline_mean: float | None
    best_total: float | None
    best_mean: float | None
    model_share_of_best: float | None
    captain_top2_model: float | None
    captain_top2_baseline: float | None
    beat_baseline: int
    beat_baseline_rate: float | None
    best_call: CallRef | None
    worst_call: CallRef | None
    mae_model: float | None = None
    mae_base: float | None = None


class SeasonOption(BaseModel):
    year: int
    phase: str
    frozen: bool
    matches: int


class SeasonPredictions(BaseModel):
    version: str
    year: int
    phase: str
    frozen: bool
    method_note: str
    credits_note: str
    wf_block: int | None = None
    seasons: list[SeasonOption]
    summary: SeasonStats
    matches: list[SeasonMatch]


class XiPlayer(BaseModel):
    player_id: str
    name: str
    image_url: str | None = None
    team: str
    team_name: str
    role: str
    multiplier: float
    selected_on: float  # the number the optimiser maximised for this XI
    pred_mean: float | None
    q10: float | None
    q50: float | None
    q90: float | None
    baseline: float | None
    actual: float | None
    points: float | None  # actual x multiplier
    credits: float | None = None


class XiCard(BaseModel):
    key: str  # model | baseline | best
    label: str
    picks: list[XiPlayer]
    captain: str | None
    vice_captain: str | None
    actual_points: float | None
    selected_on: float
    credits_total: float | None = None
    credits_complete: bool = False
    overlap_with_best: int = 0


class PlayerRow(ml.MatchPlayer):
    actual_rank: int | None = None
    credits: float | None = None


class MatchTotals(BaseModel):
    model: float | None
    baseline: float | None
    best: float | None
    model_minus_baseline: float | None
    model_share_of_best: float | None
    captain_top2_model: bool | None
    captain_top2_baseline: bool | None
    mae_model: float | None
    mae_base: float | None
    coverage: float | None


class MatchPrediction(BaseModel):
    version: str
    year: int | None
    phase: str
    frozen: bool
    method_note: str
    credits_note: str
    credits_season: int | None = None
    match: MatchHeader
    xis: dict[str, XiCard | None]
    players: list[PlayerRow]
    totals: MatchTotals


# --------------------------------------------------------------------------- lookups
def _protocol(version: str) -> tuple[int, int, int | None]:
    t = ml.telemetry_or_empty(version)
    test_y = int(ml.num(ml.get(t, "protocol", "test_season")) or 2025)
    wf_y = int(ml.num(ml.get(t, "protocol", "wf_season")) or 2026)
    block = ml.num(ml.get(t, "protocol", "wf_block"))
    return test_y, wf_y, int(block) if block is not None else None


def _latest() -> str:
    v = ml.latest_version()
    if v is None:
        runs = [r for r in ml.list_runs(include_db=False) if r.has_eval_frame]
        v = runs[0].version if runs else None
    if v is None:
        raise ml.NotFound("no trained model run yet")
    return v


def _seasons(version: str) -> list[SeasonOption]:
    df = ml._frame(version)
    test_y, wf_y, _ = _protocol(version)
    out = []
    for phase, year in (("walkforward", wf_y), ("test", test_y)):
        n = int(df.loc[df["phase"] == phase, "match_id"].nunique())
        if n:
            out.append(SeasonOption(year=year, phase=phase, frozen=phase == "test", matches=n))
    return out


def _headers(ids: Iterable[int]) -> dict[int, MatchHeader]:
    """match id -> header from the seasons store (team eras, venue photo, result); {} on error."""
    ids = [int(i) for i in ids]
    try:
        from . import seasons_data as data
        from .home_phase import match_title
        from .seasons_refs import match_summary

        core = data.core()
        out = {}
        for mid in ids:
            m = core.by_id.get(mid)
            if m is None:
                continue
            s = match_summary(core, m)
            out[mid] = MatchHeader(
                match_id=mid,
                date=s.date.isoformat(),
                season=s.season,
                match_number=s.match_number,
                stage=s.stage,
                title=match_title(s.stage, s.match_number),
                team1=TeamSide(id=s.team1.id, name=s.team1.name, short_code=s.team1.short_code),
                team2=TeamSide(id=s.team2.id, name=s.team2.name, short_code=s.team2.short_code),
                venue=s.venue,
                venue_name=s.venue.name if s.venue else None,
                city=s.venue.city if s.venue else None,
                winner_id=s.winner_id,
                result_text=s.result_text,
                scores=s.scores,
            )
        return out
    except Exception:  # DB down: fall back to the Lab's (telemetry) match info
        log.debug("predictions: match headers unavailable", exc_info=True)
        return {}


def _header_from_info(info: ml.MatchInfo) -> MatchHeader:
    def side(t: ml.TeamRef | None) -> TeamSide | None:
        return None if t is None else TeamSide(id=t.id, name=t.name, short_code=t.code)

    title = info.stage or (f"Match {info.match_number}" if info.match_number else "Match")
    return MatchHeader(
        match_id=info.match_id,
        date=info.date,
        season=info.season,
        match_number=info.match_number,
        stage=info.stage,
        title=title,
        team1=side(info.team1),
        team2=side(info.team2),
        venue_name=info.venue,
        city=info.city,
    )


def _credits(year: int) -> tuple[int | None, dict[str, float]]:
    """(credits season actually used, {player_id: credits}); 2025 stands in for 2026."""
    try:
        from ..core import db
        from ..registry.credits import credits_for_season

        with db.engine().connect() as c:
            eff, mp = credits_for_season(c, year)
        return eff, {k: float(v) for k, v in mp.items()}
    except Exception:
        return None, {}


def _credits_note(eff: int | None) -> str:
    return CREDITS_NOTE.format(season=eff if eff is not None else "no")


def _rank(players: list[ml.MatchPlayer]) -> dict[str, int]:
    """Competition rank by actual points (1 = top scorer); ties share the better rank."""
    acts = sorted((p.actual for p in players if p.actual is not None), reverse=True)
    return {
        p.player_id: 1 + sum(a > p.actual for a in acts) for p in players if p.actual is not None
    }


def _top2(rank: dict[str, int], pid: str | None) -> bool | None:
    if pid is None or not rank:
        return None
    r = rank.get(pid)
    return None if r is None else r <= 2


def _mean(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 2) if xs else None


def _rate(xs: list[bool]) -> float | None:
    return round(sum(xs) / len(xs), 4) if xs else None


def _diff(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else round(a - b, 2)


# --------------------------------------------------------------------------- season
def _frame_players(g: Any) -> list[ml.MatchPlayer]:
    """Eval-frame rows of one match -> the Lab's MatchPlayer (ids for names; no DB)."""
    out = []
    for r in g.to_dict("records"):
        out.append(
            ml.MatchPlayer(
                player_id=str(r["player_id"]),
                name=str(r.get("player_name") or r["player_id"]),
                team=str(r.get("team_id")),
                team_name=str(r.get("team_id")),
                role=str(r.get("role") or "BAT"),
                pred_mean=ml._r(r.get("pred_mean")),
                q10=ml._r(r.get("pred_q10")),
                q50=ml._r(r.get("pred_q50")),
                q90=ml._r(r.get("pred_q90")),
                baseline=ml._r(r.get("pred_base")),
                actual=ml._r(r.get("total")),
            )
        )
    return out


def _team_code(team_id: str, h: MatchHeader) -> str:
    for t in (h.team1, h.team2):
        if t is not None and str(t.id) == str(team_id):
            return t.short_code
    return team_id[:4].upper()


def _season_build(version: str, year: int) -> SeasonPredictions:
    test_y, wf_y, block = _protocol(version)
    phase = "walkforward" if year == wf_y else "test" if year == test_y else None
    if phase is None:
        raise ml.NotFound(f"run {version!r} has no honest predictions for {year}")
    df = ml._frame(version)
    sub = df[df["phase"] == phase]
    if sub.empty:
        raise ml.NotFound(f"run {version!r} has no {phase} predictions for {year}")
    rows = {r.info.match_id: r for r in ml.matches(version, phase)}
    headers = _headers(rows)
    built: list[tuple[SeasonMatch, str | None]] = []
    for mid, g in sub.groupby("match_id", sort=False):
        mid = int(mid)  # type: ignore[call-overload]
        r = rows.get(mid)
        h = headers.get(mid) or (_header_from_info(r.info) if r else None)
        if h is None:
            h = MatchHeader(match_id=mid, title="Match")
        players = _frame_players(g)
        rank = _rank(players)
        model = ml.solve_xi(players, lambda p: p.pred_mean)
        xi_model = (r.xi_model if r else None) or (model.actual_points if model else None)
        xi_base = r.xi_base if r else None
        xi_best = r.xi_best if r else None
        if xi_base is None or xi_best is None:  # telemetry lacks per-match XI totals
            b = ml.solve_xi(players, lambda p: p.baseline)
            h_ = ml.solve_xi(players, lambda p: p.actual)
            xi_base = xi_base if xi_base is not None else (b.actual_points if b else None)
            xi_best = xi_best if xi_best is not None else (h_.actual_points if h_ else None)
        cap = None
        if model and model.captain:
            p = next(x for x in players if x.player_id == model.captain)
            cap = CaptainCall(
                player=PlayerLite(
                    id=p.player_id,
                    name=p.name,
                    team=_team_code(p.team, h),
                    role=p.role,
                ),
                predicted=p.pred_mean,
                actual=p.actual,
                points=None if p.actual is None else round(p.actual * 2, 2),
                actual_rank=rank.get(p.player_id),
                top2=r.cap_hit_model
                if r and r.cap_hit_model is not None
                else _top2(rank, p.player_id),
            )
        base_hit = r.cap_hit_base if r else None
        if base_hit is None:
            b = ml.solve_xi(players, lambda p: p.baseline)
            base_hit = _top2(rank, b.captain if b else None)
        diff = _diff(xi_model, xi_base)
        built.append(
            (
                SeasonMatch(
                    match=h,
                    n_players=len(players),
                    model_xi_points=xi_model,
                    baseline_xi_points=xi_base,
                    best_xi_points=xi_best,
                    model_minus_baseline=diff,
                    model_beat_baseline=None if diff is None else diff > 0,
                    captain=cap,
                    baseline_captain_top2=base_hit,
                    mae_model=r.mae_model if r else None,
                    mae_base=r.mae_base if r else None,
                    coverage=r.covered if r else None,
                ),
                cap.player.id if cap else None,
            )
        )
    refs = ml._player_refs([pid for _, pid in built if pid])
    for m, pid in built:
        if m.captain and pid in refs:
            m.captain.player.name, m.captain.player.image_url = refs[pid]
    ms = [m for m, _ in built]
    ms.sort(key=lambda m: (m.match.date or "", m.match.match_id))
    eff, _ = _credits(year)
    return SeasonPredictions(
        version=version,
        year=year,
        phase=phase,
        frozen=phase == "test",
        method_note=METHOD_NOTE if phase == "walkforward" else FROZEN_NOTE,
        credits_note=_credits_note(eff),
        wf_block=block,
        seasons=_seasons(version),
        summary=_stats(ms),
        matches=ms,
    )


def _stats(ms: list[SeasonMatch]) -> SeasonStats:
    model = [m.model_xi_points for m in ms if m.model_xi_points is not None]
    base = [m.baseline_xi_points for m in ms if m.baseline_xi_points is not None]
    best = [m.best_xi_points for m in ms if m.best_xi_points is not None]
    diffs = [m for m in ms if m.model_minus_baseline is not None]
    beat = sum(bool(m.model_beat_baseline) for m in diffs)

    def call(m: SeasonMatch | None) -> CallRef | None:
        if m is None or m.model_minus_baseline is None:
            return None
        return CallRef(
            match_id=m.match.match_id, title=m.match.title, margin=m.model_minus_baseline
        )

    by_margin = sorted(diffs, key=lambda m: m.model_minus_baseline or 0.0)
    mm, mb = _mean(model), _mean(best)
    return SeasonStats(
        matches=len(ms),
        model_total=round(sum(model), 2) if model else None,
        model_mean=mm,
        baseline_total=round(sum(base), 2) if base else None,
        baseline_mean=_mean(base),
        best_total=round(sum(best), 2) if best else None,
        best_mean=mb,
        model_share_of_best=round(mm / mb, 4) if mm is not None and mb else None,
        captain_top2_model=_rate(
            [m.captain.top2 for m in ms if m.captain and m.captain.top2 is not None]
        ),
        captain_top2_baseline=_rate(
            [m.baseline_captain_top2 for m in ms if m.baseline_captain_top2 is not None]
        ),
        beat_baseline=beat,
        beat_baseline_rate=round(beat / len(diffs), 4) if diffs else None,
        best_call=call(by_margin[-1] if by_margin else None),
        worst_call=call(by_margin[0] if by_margin else None),
        mae_model=_mean([m.mae_model for m in ms if m.mae_model is not None]),
        mae_base=_mean([m.mae_base for m in ms if m.mae_base is not None]),
    )


def season(year: int, version: str | None = None) -> SeasonPredictions:
    v = version or _latest()
    return ml._cached(f"pred:season:{v}:{year}", ml._run_stamp(v), lambda: _season_build(v, year))


def seasons(version: str | None = None) -> list[SeasonOption]:
    return _seasons(version or _latest())


# --------------------------------------------------------------------------- match
_LABEL = {"model": "Model XI", "baseline": "Baseline XI", "best": "Best possible XI"}


def _card(
    key: str,
    xi: ml.XiResult | None,
    by_id: dict[str, ml.MatchPlayer],
    credits: dict[str, float],
    best: set[str],
) -> XiCard | None:
    if xi is None:
        return None
    picks = []
    for pk in xi.picks:
        p = by_id[pk.player_id]
        picks.append(
            XiPlayer(
                player_id=p.player_id,
                name=p.name,
                image_url=p.image_url,
                team=p.team,
                team_name=p.team_name,
                role=pk.role,
                multiplier=pk.multiplier,
                selected_on=pk.value,
                pred_mean=p.pred_mean,
                q10=p.q10,
                q50=p.q50,
                q90=p.q90,
                baseline=p.baseline,
                actual=p.actual,
                points=pk.points,
                credits=credits.get(p.player_id),
            )
        )
    cr = [x.credits for x in picks if x.credits is not None]
    return XiCard(
        key=key,
        label=_LABEL[key],
        picks=picks,
        captain=xi.captain,
        vice_captain=xi.vice_captain,
        actual_points=xi.actual_points,
        selected_on=xi.selected_on,
        credits_total=round(sum(cr), 1) if cr else None,
        credits_complete=bool(picks) and len(cr) == len(picks),
        overlap_with_best=sum(x.player_id in best for x in picks),
    )


def _match_build(version: str, match_id: int) -> MatchPrediction:
    df = ml._frame(version)
    g = df[df["match_id"] == match_id]
    if g.empty:
        raise ml.NotFound(f"no honest prediction for match {match_id}")
    phase = str(g["phase"].iloc[0])
    if phase not in PHASES:  # cross-validation rows are not pre-match predictions
        raise ml.NotFound(f"no honest prediction for match {match_id}")
    test_y, wf_y, _ = _protocol(version)
    year = wf_y if phase == "walkforward" else test_y
    d = ml.match_detail(version, match_id)
    h = _headers([match_id]).get(match_id) or _header_from_info(d.info)
    eff, credits = _credits(year)
    rank = _rank(d.players)
    by_id = {p.player_id: p for p in d.players}
    hind = d.xi.get("hindsight")
    best_ids = {x.player_id for x in hind.picks} if hind else set()
    xis = {
        "model": _card("model", d.xi.get("model"), by_id, credits, best_ids),
        "baseline": _card("baseline", d.xi.get("baseline"), by_id, credits, best_ids),
        "best": _card("best", d.xi.get("hindsight"), by_id, credits, best_ids),
    }
    players = [
        PlayerRow(
            **p.model_dump(), actual_rank=rank.get(p.player_id), credits=credits.get(p.player_id)
        )
        for p in d.players
    ]
    pts = {k: (x.actual_points if x else None) for k, x in xis.items()}
    tel = ml._per_match(ml.telemetry_or_empty(version), phase).get(match_id, {})
    hit_m, hit_b = tel.get("cap_hit_model"), tel.get("cap_hit_base")  # same rule as training
    return MatchPrediction(
        version=version,
        year=year,
        phase=phase,
        frozen=phase == "test",
        method_note=METHOD_NOTE if phase == "walkforward" else FROZEN_NOTE,
        credits_note=_credits_note(eff),
        credits_season=eff,
        match=h,
        xis=xis,
        players=players,
        totals=MatchTotals(
            model=pts["model"],
            baseline=pts["baseline"],
            best=pts["best"],
            model_minus_baseline=_diff(pts["model"], pts["baseline"]),
            model_share_of_best=round(pts["model"] / pts["best"], 4)
            if pts["model"] is not None and pts["best"]
            else None,
            captain_top2_model=hit_m
            if isinstance(hit_m, bool)
            else _top2(rank, xis["model"].captain if xis["model"] else None),
            captain_top2_baseline=hit_b
            if isinstance(hit_b, bool)
            else _top2(rank, xis["baseline"].captain if xis["baseline"] else None),
            mae_model=d.mae_model,
            mae_base=d.mae_base,
            coverage=d.coverage,
        ),
    )


def match(match_id: int, version: str | None = None) -> MatchPrediction:
    v = version or _latest()
    return ml._cached(
        f"pred:match:{v}:{match_id}", ml._run_stamp(v), lambda: _match_build(v, match_id)
    )


# --------------------------------------------------------------------------- builder
class OptimiseRequest(BaseModel):
    locks: list[str] = Field(default_factory=list, max_length=11)
    excludes: list[str] = Field(default_factory=list, max_length=40)


class OptimiseResult(BaseModel):
    match_id: int
    xi: XiCard
    projected: float  # objective on the predicted means, C x2 / VC x1.5
    credits_constrained: bool
    credits_used: float | None
    budget: float | None
    note: str


def optimise(
    match_id: int,
    locks: Iterable[str] = (),
    excludes: Iterable[str] = (),
    version: str | None = None,
) -> OptimiseResult:
    """Re-run the optimiser on a match's honest predictions, honouring locks / excludes.

    Dream11 rules (11 players, 1-8 per role, max 10 per team, C x2 / VC x1.5); the 100-credit
    cap applies only when every remaining candidate has credits, otherwise the XI is uncapped.
    Raises ``ValueError`` (incl. ``Infeasible``) for unknown ids or impossible constraints.
    """
    from ..optimize.xi import DREAM11, Candidate, Options, solve

    d = match(match_id, version)
    lk, ex = frozenset(locks), frozenset(excludes)
    ids = {p.player_id for p in d.players}
    if unknown := (lk | ex) - ids:
        raise ValueError(f"players not in match {match_id}: {sorted(unknown)}")
    pool = [
        Candidate(
            p.player_id, p.team, p.role if p.role in ml.ROLES else "BAT", p.pred_mean, p.credits
        )
        for p in d.players
        if p.pred_mean is not None
    ]
    sel = solve(pool, options=Options(locks=lk, excludes=ex, use_credits=True))
    by_id = {p.player_id: p for p in d.players}
    best = {x.player_id for x in d.xis["best"].picks} if d.xis.get("best") else set()
    picks = []
    for pk in sel.picks:
        p = by_id[pk.candidate.player]
        picks.append(
            XiPlayer(
                player_id=p.player_id,
                name=p.name,
                image_url=p.image_url,
                team=p.team,
                team_name=p.team_name,
                role=pk.candidate.role,
                multiplier=pk.multiplier,
                selected_on=round(pk.candidate.value, 2),
                pred_mean=p.pred_mean,
                q10=p.q10,
                q50=p.q50,
                q90=p.q90,
                baseline=p.baseline,
                actual=p.actual,
                points=None if p.actual is None else round(p.actual * pk.multiplier, 2),
                credits=p.credits,
            )
        )
    cr = [x.credits for x in picks if x.credits is not None]
    has_actual = all(x.actual is not None for x in picks)
    card = XiCard(
        key="model",
        label="Your XI" if lk or ex else _LABEL["model"],
        picks=picks,
        captain=sel.captain,
        vice_captain=sel.vice_captain,
        actual_points=round(sum(x.points or 0.0 for x in picks), 2) if has_actual else None,
        selected_on=round(sel.total, 2),
        credits_total=round(sum(cr), 1) if cr else None,
        credits_complete=len(cr) == len(picks),
        overlap_with_best=sum(x.player_id in best for x in picks),
    )
    capped = sel.credits_constrained
    note = (
        f"Credit cap {DREAM11.budget:g} applied ({d.credits_season} credits)."
        if capped
        else "Uncapped: not every available player has credits, so the 100-credit cap is off."
    )
    return OptimiseResult(
        match_id=match_id,
        xi=card,
        projected=round(sel.total, 2),
        credits_constrained=capped,
        credits_used=card.credits_total,
        budget=DREAM11.budget if capped else None,
        note=note,
    )


def warm() -> None:
    """Build the latest walk-forward season (and its match pages lazily) off the request path."""
    try:
        v = _latest()
        _, wf_y, _ = _protocol(v)
        season(wf_y, v)
    except Exception:
        log.debug("predictions warm-up skipped", exc_info=True)
