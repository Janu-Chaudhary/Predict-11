"""Model Lab: read-only views over trained fantasy-points model runs.

A run lives in ``<models_dir>/<version>/`` (written by ``p11 model train``):

- ``telemetry.json``  everything the Lab charts (protocol, data, features, curves, metrics, ...)
- ``{mean,q10,q50,q90}.txt``  LightGBM boosters (the serving model)
- ``eval_frame.parquet``  ids + features + ``total`` + ``pred_*`` for the test / walk-forward rows
- ``meta.json``  params, trees, features
- ``<models_dir>/latest.json``  ``{"version": ...}``

Every reader is tolerant: a missing file or key degrades to ``None`` / empty instead of failing,
because the training code and this reader evolve independently. ``P11_MODELS_DIR`` overrides the
directory (tests and UI previews point it at a synthetic run; the repo's ``models/`` is never
written here).
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
import math
import os
import re
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..core.settings import REPO_ROOT

VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PHASES = ("test", "walkforward")
ROLES = ("WK", "BAT", "AR", "BOWL")
HEADLINE_METRICS = ("best_xi_points", "captain_top2_rate", "mae", "spearman")


class NotFound(LookupError):
    pass


# --------------------------------------------------------------------------- paths
def models_dir() -> Path:
    env = os.environ.get("P11_MODELS_DIR")
    return Path(env).expanduser() if env else REPO_ROOT / "models"


def run_dir(version: str) -> Path:
    if not VERSION_RE.match(version):
        raise NotFound(f"no model run {version!r}")
    d = models_dir() / version
    if not d.is_dir():
        raise NotFound(f"no model run {version!r}")
    return d


def _stamp(p: Path) -> tuple[int, int] | None:
    try:
        st = p.stat()
    except OSError:
        return None
    return (st.st_mtime_ns, st.st_size)


# --------------------------------------------------------------------------- small cache
@dataclass
class _Entry:
    stamp: Any
    value: Any


_cache: dict[str, _Entry] = {}
_lock = threading.Lock()


def _cached[T](key: str, stamp: Any, build: Callable[[], T]) -> T:
    with _lock:
        e = _cache.get(key)
        if e is not None and e.stamp == stamp:
            return e.value  # type: ignore[no-any-return]
    value = build()
    with _lock:
        _cache[key] = _Entry(stamp, value)
        if len(_cache) > 256:  # crude bound: drop the oldest half
            for k in list(_cache)[:128]:
                _cache.pop(k, None)
    return value


# --------------------------------------------------------------------------- tolerant access
def get(d: Any, *path: str | int, default: Any = None) -> Any:
    """``get(t, "evaluations", "test:2025", "mae")`` without KeyErrors / TypeErrors."""
    cur = d
    for k in path:
        if isinstance(cur, dict):
            cur = cur.get(k)  # type: ignore[call-overload]
        elif isinstance(cur, list) and isinstance(k, int) and -len(cur) <= k < len(cur):
            cur = cur[k]
        else:
            return default
        if cur is None:
            return default
    return cur


def num(x: Any) -> float | None:
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _clean(o: Any) -> Any:
    """NaN/inf -> None recursively (JSON has no NaN; browsers reject it)."""
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, list | tuple):
        return [_clean(v) for v in o]
    return o


def phase_key(evals: dict | None, phase: str) -> str | None:
    """The telemetry key for a phase: ``test`` -> ``test:2025`` (first match)."""
    if not isinstance(evals, dict):
        return None
    for k in evals:
        if k == phase or k.startswith(f"{phase}:"):
            return k
    return None


# --------------------------------------------------------------------------- telemetry
@dataclass(frozen=True)
class Telemetry:
    data: dict
    body: bytes  # canonical JSON (NaN-free)
    gz: bytes
    etag: str


def _read_telemetry(path: Path) -> Telemetry:
    raw = json.loads(path.read_text(), parse_constant=lambda _c: None)
    data = _clean(raw) if isinstance(raw, dict) else {}
    body = json.dumps(data, separators=(",", ":"), allow_nan=False).encode()
    st = path.stat()
    return Telemetry(data, body, gzip.compress(body, 6), f"{st.st_mtime_ns:x}{st.st_size:x}")


def telemetry(version: str) -> Telemetry:
    p = run_dir(version) / "telemetry.json"
    stamp = _stamp(p)
    if stamp is None:
        raise NotFound(f"run {version!r} has no telemetry.json yet")
    return _cached(f"tel:{p}", stamp, lambda: _read_telemetry(p))


def telemetry_or_empty(version: str) -> dict:
    try:
        return telemetry(version).data
    except NotFound:
        return {}


def _meta(version: str) -> dict:
    p = models_dir() / version / "meta.json"
    stamp = _stamp(p)
    if stamp is None:
        return {}

    def build() -> dict:
        try:
            m = json.loads(p.read_text(), parse_constant=lambda _c: None)
        except (OSError, ValueError):
            return {}
        return _clean(m) if isinstance(m, dict) else {}

    return _cached(f"meta:{p}", stamp, build)


# --------------------------------------------------------------------------- runs
class MetricPair(BaseModel):
    model: float | None = None
    baseline: float | None = None
    diff: float | None = None
    ci95: list[float | None] = Field(default_factory=list)


class PhaseHeadline(BaseModel):
    key: str
    matches: int | None = None
    best_xi_points: MetricPair | None = None
    hindsight_best_xi_points: float | None = None
    captain_top2_rate: MetricPair | None = None
    mae: MetricPair | None = None
    spearman: MetricPair | None = None
    p10_p90_coverage: float | None = None


class RunSummary(BaseModel):
    version: str
    created_at: str | None = None
    is_latest: bool = False
    has_telemetry: bool = False
    has_eval_frame: bool = False
    has_booster: bool = False
    in_db: bool = False
    n_features: int | None = None
    n_learned_values: int | None = None
    trees: dict[str, int] = Field(default_factory=dict)
    duration_s: float | None = None
    chosen_params: dict[str, Any] = Field(default_factory=dict)
    test: PhaseHeadline | None = None
    walkforward: PhaseHeadline | None = None


def _pair(x: Any) -> MetricPair | None:
    if not isinstance(x, dict):
        return None
    ci = x.get("ci95") if isinstance(x.get("ci95"), list) else []
    return MetricPair(
        model=num(x.get("model")),
        baseline=num(x.get("baseline")),
        diff=num(x.get("diff")),
        ci95=[num(v) for v in ci[:2]],
    )


def headline(key: str, s: Any) -> PhaseHeadline | None:
    if not isinstance(s, dict):
        return None
    m = num(s.get("matches"))
    return PhaseHeadline(
        key=key,
        matches=int(m) if m is not None else None,
        best_xi_points=_pair(s.get("best_xi_points")),
        hindsight_best_xi_points=num(s.get("hindsight_best_xi_points")),
        captain_top2_rate=_pair(s.get("captain_top2_rate")),
        mae=_pair(s.get("mae")),
        spearman=_pair(s.get("spearman")),
        p10_p90_coverage=num(s.get("p10_p90_coverage")),
    )


def _int_map(x: Any) -> dict[str, int]:
    if not isinstance(x, dict):
        return {}
    return {str(k): int(v) for k, v in x.items() if num(v) is not None}


def latest_version() -> str | None:
    p = models_dir() / "latest.json"
    try:
        v = json.loads(p.read_text()).get("version")
    except (OSError, ValueError, AttributeError):
        return None
    return v if isinstance(v, str) and VERSION_RE.match(v) else None


def _summary_from_files(d: Path) -> RunSummary:
    v = d.name
    t = telemetry_or_empty(v)
    meta = _meta(v)
    evals = t.get("evaluations") if isinstance(t.get("evaluations"), dict) else {}
    tk, wk = phase_key(evals, "test"), phase_key(evals, "walkforward")
    feats = t.get("features") if isinstance(t.get("features"), list) else None
    n_features = len(feats) if feats else len(meta.get("features") or []) or None
    created = t.get("created_at") or meta.get("created_at")
    if created is None and (st := _stamp(d)) is not None:
        created = dt.datetime.fromtimestamp(st[0] / 1e9, dt.UTC).isoformat(timespec="seconds")
    return RunSummary(
        version=v,
        created_at=str(created) if created else None,
        has_telemetry=(d / "telemetry.json").is_file(),
        has_eval_frame=(d / "eval_frame.parquet").is_file(),
        has_booster=(d / "mean.txt").is_file(),
        n_features=n_features,
        n_learned_values=int(x)
        if (x := num(t.get("n_learned_values") or meta.get("n_learned_values"))) is not None
        else None,
        trees=_int_map(t.get("trees") or meta.get("trees")),
        duration_s=num(get(t, "duration_s", "total")) or num(meta.get("seconds")),
        chosen_params=t.get("chosen_params") or meta.get("params") or {},
        test=headline(tk, evals[tk]) if tk else None,
        walkforward=headline(wk, evals[wk]) if wk else None,
    )


def _db_runs() -> list[dict]:
    """model_run rows when the table exists and the DB is up; [] otherwise."""
    try:
        from sqlalchemy import text

        from ..core import db

        with db.engine().connect() as c:
            if c.execute(text("SELECT to_regclass('model_run')")).scalar() is None:
                return []
            rows = c.execute(
                text("SELECT version, created_at, metrics, params, n_learned_values FROM model_run")
            ).mappings()
            return [dict(r) for r in rows]
    except Exception:  # DB down / schema drift: the files are the source of truth
        return []


def list_runs(include_db: bool = True) -> list[RunSummary]:
    root = models_dir()
    runs: dict[str, RunSummary] = {}
    if root.is_dir():
        for d in root.iterdir():
            if (
                d.is_dir()
                and VERSION_RE.match(d.name)
                and ((d / "telemetry.json").is_file() or (d / "meta.json").is_file())
            ):
                runs[d.name] = _summary_from_files(d)
    for r in _db_runs() if include_db else []:
        v = str(r["version"])
        s = runs.get(v)
        if s is None:
            m = r.get("metrics") or {}
            p = r.get("params") or {}
            s = RunSummary(
                version=v,
                n_learned_values=r.get("n_learned_values"),
                trees=_int_map(p.get("trees")),
                chosen_params=p.get("params") or {},
                test=headline("test", _clean(m.get("test_2025"))),
                walkforward=headline("walkforward", _clean(m.get("walkforward_2026"))),
            )
            runs[v] = s
        s.in_db = True
        if r.get("created_at") is not None and not s.created_at:
            s.created_at = r["created_at"].isoformat(timespec="seconds")
    latest = latest_version()
    out = sorted(runs.values(), key=lambda s: (s.created_at or "", s.version), reverse=True)
    if latest is None and out:
        latest = next((s.version for s in out if s.has_telemetry), out[0].version)
    for s in out:
        s.is_latest = s.version == latest
    return out


# --------------------------------------------------------------------------- eval frame
def _frame(version: str):  # type: ignore[no-untyped-def]
    import pandas as pd

    p = run_dir(version) / "eval_frame.parquet"
    stamp = _stamp(p)
    if stamp is None:
        raise NotFound(f"run {version!r} has no eval_frame.parquet")

    def build() -> pd.DataFrame:
        df = pd.read_parquet(p)
        t = telemetry_or_empty(version)
        test_y = num(get(t, "protocol", "test_season")) or 2025
        wf_y = num(get(t, "protocol", "wf_season")) or 2026
        if "phase" in df.columns:
            df["phase"] = df["phase"].astype(str).str.split(":").str[0]
        elif "year" in df.columns:
            df["phase"] = df["year"].map(
                lambda y: "test" if y == test_y else "walkforward" if y == wf_y else "cv"
            )
        else:
            df["phase"] = "test"
        if "role" not in df.columns and "role_code" in df.columns:
            df["role"] = df["role_code"].map(
                lambda c: ROLES[int(c)] if num(c) is not None else "BAT"
            )
        if "pred_base" not in df.columns:
            df["pred_base"] = df["mean_5"].fillna(0.0) if "mean_5" in df.columns else 0.0
        if "team_id" not in df.columns and "team" in df.columns:
            df["team_id"] = df["team"]
        df["match_id"] = df["match_id"].astype("int64")
        df["player_id"] = df["player_id"].astype(str)
        return df

    return _cached(f"frame:{p}", stamp, build)


def _run_stamp(version: str) -> tuple:
    d = run_dir(version)
    return (_stamp(d / "eval_frame.parquet"), _stamp(d / "telemetry.json"))


# --------------------------------------------------------------------------- DB lookups
class TeamRef(BaseModel):
    id: int | str | None = None
    name: str
    code: str


class MatchInfo(BaseModel):
    match_id: int
    date: str | None = None
    season: int | None = None
    match_number: int | None = None
    stage: str | None = None
    team1: TeamRef | None = None
    team2: TeamRef | None = None
    venue: str | None = None
    city: str | None = None


def _match_meta(ids: Iterable[int]) -> dict[int, MatchInfo]:
    ids = [int(i) for i in ids]
    if not ids:
        return {}
    try:
        from sqlalchemy import text

        from ..core import db
        from .home_phase import team_code, team_display

        with db.engine().connect() as c:
            rows = c.execute(
                text(
                    """SELECT m.id, m.start_date, m.match_number, m.stage, s.year,
                              m.team1_id, t1.name AS t1, m.team2_id, t2.name AS t2,
                              v.name AS venue, v.city
                       FROM match m JOIN season s ON s.id = m.season_id
                       JOIN team t1 ON t1.id = m.team1_id JOIN team t2 ON t2.id = m.team2_id
                       LEFT JOIN venue v ON v.id = m.venue_id
                       WHERE m.id = ANY(:ids)"""
                ),
                {"ids": ids},
            ).mappings()
            out = {}
            for r in rows:
                y = r["year"]
                out[int(r["id"])] = MatchInfo(
                    match_id=int(r["id"]),
                    date=r["start_date"].isoformat() if r["start_date"] else None,
                    season=y,
                    match_number=r["match_number"],
                    stage=r["stage"],
                    team1=TeamRef(
                        id=r["team1_id"], name=team_display(r["t1"], y), code=team_code(r["t1"], y)
                    ),
                    team2=TeamRef(
                        id=r["team2_id"], name=team_display(r["t2"], y), code=team_code(r["t2"], y)
                    ),
                    venue=r["venue"],
                    city=r["city"],
                )
            return out
    except Exception:
        return {}


def _player_refs(ids: Iterable[str]) -> dict[str, tuple[str, str | None]]:
    """player id -> (display name, image url); {} when the DB is unavailable."""
    try:
        from ..core import db
        from .players_identity import player_refs

        with db.engine().connect() as c:
            refs = player_refs(c, ids)
        return {k: (r.display_name or r.name, r.image_url) for k, r in refs.items()}
    except Exception:
        return {}


def _team_ref(team_id: Any, info: MatchInfo | None) -> TeamRef:
    for t in (info.team1, info.team2) if info else ():
        if t is not None and str(t.id) == str(team_id):
            return t
    s = str(team_id)
    return TeamRef(id=s, name=s, code=s[:4].upper())


def _fallback_info(mid: int, row: dict | None) -> MatchInfo:
    """From telemetry per_match when the DB is unavailable."""
    row = row or {}

    def team(x: Any) -> TeamRef | None:
        if x is None:
            return None
        s = str(x)
        return TeamRef(id=s, name=s, code=s if len(s) <= 4 else s[:4].upper())

    return MatchInfo(
        match_id=mid,
        date=str(row["date"])[:10] if row.get("date") else None,
        team1=team(row.get("team1")),
        team2=team(row.get("team2")),
    )


# --------------------------------------------------------------------------- matches
class MatchRow(BaseModel):
    info: MatchInfo
    phase: str
    n_players: int
    mae_model: float | None = None
    mae_base: float | None = None
    xi_model: float | None = None
    xi_base: float | None = None
    xi_best: float | None = None
    cap_hit_model: bool | None = None
    cap_hit_base: bool | None = None
    rho_model: float | None = None
    rho_base: float | None = None
    covered: float | None = None


def _per_match(t: dict, phase: str) -> dict[int, dict]:
    pm = t.get("per_match") if isinstance(t.get("per_match"), dict) else {}
    k = phase_key(pm, phase)
    rows = pm.get(k) if k else None
    out: dict[int, dict] = {}
    for r in rows if isinstance(rows, list) else []:
        if isinstance(r, dict) and num(r.get("match_id")) is not None:
            out[int(r["match_id"])] = r
    return out


def matches(version: str, phase: str) -> list[MatchRow]:
    if phase not in PHASES:
        raise ValueError(f"phase must be one of {PHASES}")
    df = _frame(version)
    t = telemetry_or_empty(version)

    def build() -> list[MatchRow]:
        sub = df[df["phase"] == phase]
        pm = _per_match(t, phase)
        ids = [int(x) for x in sub["match_id"].unique()]
        meta = _match_meta(ids)
        has_total = "total" in sub.columns
        out = []
        for mid, g in sub.groupby("match_id", sort=False):
            mid = int(mid)  # type: ignore[call-overload]
            r = pm.get(mid, {})
            info = meta.get(mid) or _fallback_info(mid, r)
            if info.date is None and "date" in g.columns:
                info.date = str(g["date"].iloc[0])[:10]
            mae_m = (g["pred_mean"] - g["total"]).abs().mean() if has_total else None
            mae_b = (g["pred_base"] - g["total"]).abs().mean() if has_total else None
            out.append(
                MatchRow(
                    info=info,
                    phase=phase,
                    n_players=len(g),
                    mae_model=num(r.get("mae_model")) or num(mae_m),
                    mae_base=num(r.get("mae_base")) or num(mae_b),
                    xi_model=num(r.get("xi_model")),
                    xi_base=num(r.get("xi_base")),
                    xi_best=num(r.get("xi_best")),
                    cap_hit_model=r.get("cap_hit_model"),
                    cap_hit_base=r.get("cap_hit_base"),
                    rho_model=num(r.get("rho_model")),
                    rho_base=num(r.get("rho_base")),
                    covered=num(r.get("covered")),
                )
            )
        out.sort(key=lambda m: (m.info.date or "", m.info.match_id))
        return out

    return _cached(f"matches:{version}:{phase}", _run_stamp(version), build)


class XiPick(BaseModel):
    player_id: str
    name: str
    image_url: str | None = None
    team: str
    role: str
    multiplier: float
    value: float  # what the selector optimised (prediction / baseline / actual)
    actual: float | None
    points: float | None  # actual x multiplier


class XiResult(BaseModel):
    picks: list[XiPick]
    captain: str | None
    vice_captain: str | None
    actual_points: float | None  # scored with actual points (C x2, VC x1.5)
    selected_on: float  # objective value on the selector's own numbers


class MatchPlayer(BaseModel):
    player_id: str
    name: str
    image_url: str | None = None
    team: str
    team_name: str
    role: str
    pred_mean: float | None
    q10: float | None
    q50: float | None
    q90: float | None
    baseline: float | None
    actual: float | None
    in_model_xi: bool = False
    in_base_xi: bool = False
    in_best_xi: bool = False
    model_mult: float | None = None
    base_mult: float | None = None
    best_mult: float | None = None


class MatchDetail(BaseModel):
    version: str
    info: MatchInfo
    phase: str
    players: list[MatchPlayer]
    xi: dict[str, XiResult | None]
    mae_model: float | None = None
    mae_base: float | None = None
    coverage: float | None = None


def solve_xi(
    players: list[MatchPlayer], value: Callable[[MatchPlayer], float | None]
) -> XiResult | None:
    """Best Dream11 XI (C x2 / VC x1.5, no credit cap) on ``value``; scored with actual points.

    Shared with the 2026 predicted-XI views (``p11.analytics.predictions``).
    """
    from ..optimize.xi import Candidate, Infeasible, Options, solve

    pool = [
        Candidate(p.player_id, p.team, p.role if p.role in ROLES else "BAT", v)
        for p in players
        if (v := value(p)) is not None
    ]
    try:
        sel = solve(pool, options=Options(use_credits=False))
    except (Infeasible, ValueError):
        return None
    by_id = {p.player_id: p for p in players}
    picks = []
    for pk in sel.picks:
        p = by_id[pk.candidate.player]
        picks.append(
            XiPick(
                player_id=p.player_id,
                name=p.name,
                image_url=p.image_url,
                team=p.team,
                role=pk.candidate.role,
                multiplier=pk.multiplier,
                value=round(pk.candidate.value, 2),
                actual=p.actual,
                points=None if p.actual is None else round(p.actual * pk.multiplier, 2),
            )
        )
    has_actual = all(x.actual is not None for x in picks)
    return XiResult(
        picks=picks,
        captain=sel.captain,
        vice_captain=sel.vice_captain,
        actual_points=round(sum(x.points or 0.0 for x in picks), 2) if has_actual else None,
        selected_on=round(sel.total, 2),
    )


_xi = solve_xi


def match_detail(version: str, match_id: int) -> MatchDetail:
    df = _frame(version)

    def build() -> MatchDetail:
        g = df[df["match_id"] == match_id]
        if g.empty:
            raise NotFound(f"match {match_id} is not in run {version!r}")
        phase = str(g["phase"].iloc[0])
        t = telemetry_or_empty(version)
        info = _match_meta([match_id]).get(match_id) or _fallback_info(
            match_id, _per_match(t, phase).get(match_id)
        )
        if info.date is None and "date" in g.columns:
            info.date = str(g["date"].iloc[0])[:10]
        refs = _player_refs(g["player_id"].tolist())
        players = []
        for r in g.to_dict("records"):
            pid = str(r["player_id"])
            name, img = refs.get(pid, (str(r.get("player_name") or pid), None))
            team = _team_ref(r.get("team_id"), info)
            players.append(
                MatchPlayer(
                    player_id=pid,
                    name=name,
                    image_url=img,
                    team=team.code,
                    team_name=team.name,
                    role=str(r.get("role") or "BAT"),
                    pred_mean=_r(r.get("pred_mean")),
                    q10=_r(r.get("pred_q10")),
                    q50=_r(r.get("pred_q50")),
                    q90=_r(r.get("pred_q90")),
                    baseline=_r(r.get("pred_base")),
                    actual=_r(r.get("total")),
                )
            )
        xis = {
            "model": _xi(players, lambda p: p.pred_mean),
            "baseline": _xi(players, lambda p: p.baseline),
            "hindsight": _xi(players, lambda p: p.actual),
        }
        for key, attr in (("model", "model"), ("baseline", "base"), ("hindsight", "best")):
            x = xis[key]
            mult = {pk.player_id: pk.multiplier for pk in x.picks} if x else {}
            for p in players:
                setattr(p, f"in_{attr}_xi", p.player_id in mult)
                setattr(p, f"{attr}_mult", mult.get(p.player_id))
        players.sort(key=lambda p: -(p.pred_mean or 0.0))
        act = [(p.pred_mean, p.baseline, p.actual, p.q10, p.q90) for p in players]
        full = [a for a in act if None not in a]
        n = len(full) or 1
        return MatchDetail(
            version=version,
            info=info,
            phase=phase,
            players=players,
            xi=xis,
            mae_model=round(sum(abs(a[0] - a[2]) for a in full) / n, 3) if full else None,
            mae_base=round(sum(abs(a[1] - a[2]) for a in full) / n, 3) if full else None,
            coverage=round(sum(a[3] <= a[2] <= a[4] for a in full) / n, 3) if full else None,
        )

    return _cached(f"match:{version}:{match_id}", _run_stamp(version), build)


def _r(x: Any, nd: int = 2) -> float | None:
    f = num(x)
    return None if f is None else round(f, nd)


# --------------------------------------------------------------------------- explain (SHAP)
class Contribution(BaseModel):
    feature: str
    group: str | None = None
    description: str | None = None
    value: float | None
    shap: float


class Explanation(BaseModel):
    version: str
    match_id: int
    player_id: str
    name: str
    team: str | None = None
    role: str | None = None
    phase: str
    base_value: float
    prediction: float  # base + sum(shap): the saved booster's output for this row
    pred_out_of_sample: float | None  # the prediction stored in the eval frame
    actual: float | None
    note: str
    contributions: list[Contribution]


def _booster(version: str):  # type: ignore[no-untyped-def]
    import lightgbm as lgb

    p = run_dir(version) / "mean.txt"
    stamp = _stamp(p)
    if stamp is None:
        raise NotFound(f"run {version!r} has no mean.txt booster")
    return _cached(f"booster:{p}", stamp, lambda: lgb.Booster(model_file=str(p)))


def explain(version: str, match_id: int, player_id: str) -> Explanation:
    import numpy as np

    df = _frame(version)
    row = df[(df["match_id"] == match_id) & (df["player_id"] == player_id)]
    if row.empty:
        raise NotFound(f"no row for player {player_id!r} in match {match_id} (run {version!r})")
    booster = _booster(version)
    feats = list(booster.feature_name())
    missing = [f for f in feats if f not in row.columns]
    if missing:
        raise NotFound(f"eval frame lacks booster features: {missing[:5]}")
    X = row[feats].astype(float)
    contrib = np.asarray(booster.predict(X, pred_contrib=True))[0]
    t = telemetry_or_empty(version)
    fmeta = {
        f.get("name"): f for f in (t.get("features") or []) if isinstance(f, dict) and f.get("name")
    }
    values = X.iloc[0].to_numpy(float)
    contribs = [
        Contribution(
            feature=f,
            group=get(fmeta, f, "group"),
            description=get(fmeta, f, "description"),
            value=None if not math.isfinite(v) else round(float(v), 4),
            shap=round(float(s), 4),
        )
        for f, v, s in zip(feats, values, contrib[:-1], strict=True)
    ]
    contribs.sort(key=lambda c: -abs(c.shap))
    r = row.iloc[0]
    refs = _player_refs([player_id])
    name = refs.get(player_id, (str(r.get("player_name") or player_id), None))[0]
    info = _match_meta([match_id]).get(match_id)
    base = float(contrib[-1])
    pred = base + float(np.sum(contrib[:-1]))
    test_y = get(t, "protocol", "test_season") or 2025
    wf_y = get(t, "protocol", "wf_season") or 2026
    return Explanation(
        version=version,
        match_id=match_id,
        player_id=player_id,
        name=name,
        team=_team_ref(r.get("team_id"), info).code if "team_id" in row.columns else None,
        role=str(r.get("role")) if "role" in row.columns else None,
        phase=str(r.get("phase")),
        base_value=round(base, 4),
        prediction=round(pred, 4),
        pred_out_of_sample=_r(r.get("pred_mean"), 4) if "pred_mean" in row.columns else None,
        actual=_r(r.get("total")) if "total" in row.columns else None,
        note=(
            "SHAP is computed with the saved mean-head booster (the serving model, trained on "
            f"seasons up to {wf_y}). The {test_y} test and {wf_y} walk-forward predictions were "
            "made by models that had not seen those matches, so this booster's output can differ "
            "slightly from the out-of-sample prediction."
        ),
        contributions=contribs,
    )


# --------------------------------------------------------------------------- compare
class MetricDelta(BaseModel):
    phase: str
    metric: str
    a: float | None
    b: float | None
    delta: float | None
    higher_is_better: bool


class ParamDiff(BaseModel):
    name: str
    a: Any = None
    b: Any = None
    changed: bool


class ImportanceDelta(BaseModel):
    feature: str
    group: str | None = None
    a_gain_share: float | None
    b_gain_share: float | None
    delta: float | None
    a_rank: int | None
    b_rank: int | None


class Comparison(BaseModel):
    a: RunSummary
    b: RunSummary
    metrics: list[MetricDelta]
    params: list[ParamDiff]
    importance: list[ImportanceDelta]
    features_only_a: list[str]
    features_only_b: list[str]


def _gain_shares(t: dict) -> dict[str, tuple[float, str | None]]:
    feats = [f for f in (t.get("features") or []) if isinstance(f, dict) and f.get("name")]
    tot = sum(num(f.get("importance_gain")) or 0.0 for f in feats) or 1.0
    return {
        f["name"]: ((num(f.get("importance_gain")) or 0.0) / tot, f.get("group")) for f in feats
    }


def compare(a: str, b: str) -> Comparison:
    ta, tb = telemetry(a).data, telemetry(b).data  # 404 if either is missing
    runs = {r.version: r for r in list_runs(include_db=False)}
    sa, sb = runs.get(a) or RunSummary(version=a), runs.get(b) or RunSummary(version=b)
    metrics: list[MetricDelta] = []
    for phase in PHASES:
        ka = phase_key(ta.get("evaluations"), phase)
        kb = phase_key(tb.get("evaluations"), phase)
        ea = get(ta, "evaluations", ka) if ka else None
        eb = get(tb, "evaluations", kb) if kb else None
        for m, hib in (
            ("best_xi_points", True),
            ("captain_top2_rate", True),
            ("mae", False),
            ("spearman", True),
        ):
            va, vb = num(get(ea, m, "model")), num(get(eb, m, "model"))
            metrics.append(
                MetricDelta(
                    phase=phase,
                    metric=m,
                    a=va,
                    b=vb,
                    delta=None if va is None or vb is None else round(vb - va, 4),
                    higher_is_better=hib,
                )
            )
        ca, cb = num(get(ea, "p10_p90_coverage")), num(get(eb, "p10_p90_coverage"))
        metrics.append(
            MetricDelta(
                phase=phase,
                metric="p10_p90_coverage",
                a=ca,
                b=cb,
                delta=None if ca is None or cb is None else round(cb - ca, 4),
                higher_is_better=True,
            )
        )
    pa, pb = ta.get("chosen_params") or {}, tb.get("chosen_params") or {}
    params = [
        ParamDiff(name=k, a=pa.get(k), b=pb.get(k), changed=pa.get(k) != pb.get(k))
        for k in sorted(set(pa) | set(pb))
    ]
    ga, gb = _gain_shares(ta), _gain_shares(tb)
    rank_a = {f: i + 1 for i, (f, _) in enumerate(sorted(ga.items(), key=lambda x: -x[1][0]))}
    rank_b = {f: i + 1 for i, (f, _) in enumerate(sorted(gb.items(), key=lambda x: -x[1][0]))}
    imp = []
    for f in set(ga) | set(gb):
        va = ga[f][0] if f in ga else None
        vb = gb[f][0] if f in gb else None
        imp.append(
            ImportanceDelta(
                feature=f,
                group=(gb.get(f) or ga.get(f) or (0, None))[1],
                a_gain_share=None if va is None else round(va, 5),
                b_gain_share=None if vb is None else round(vb, 5),
                delta=None if va is None or vb is None else round(vb - va, 5),
                a_rank=rank_a.get(f),
                b_rank=rank_b.get(f),
            )
        )
    imp.sort(key=lambda d: -abs(d.delta or 0.0))
    return Comparison(
        a=sa,
        b=sb,
        metrics=metrics,
        params=params,
        importance=imp,
        features_only_a=sorted(set(ga) - set(gb)),
        features_only_b=sorted(set(gb) - set(ga)),
    )
