"""Hero B data: the hindsight-best fantasy XI of a match from persisted points + roles.

Persisted fantasy points (``player_match_points``) and player roles (``player_attribute``) are
being added by another workstream, so their presence and exact column names are detected at
runtime. When either is missing, or has no rows for the match, ``load_xi`` returns ``None`` and
the API answers 204 (the UI then falls back to hero C). Nothing is ever invented: points are
the persisted actual points, and the "XI" is the best valid team in hindsight, not a prediction.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Connection, text

from .home_phase import team_code

ROLES = ("WK", "BAT", "AR", "BOWL")
ROLE_MIN, ROLE_MAX = 1, 8  # Dream11 T20 (2023+): 1-8 of each role
TEAM_MAX = 10  # at most 10 players from one side
XI_SIZE = 11

_POINT_COLS = ("fantasy_points", "points", "total_points", "fp", "total")
_ROLE_COLS = ("role", "fantasy_role", "dream11_role", "playing_role")
_ROLE_ALIASES = {
    "WK": "WK",
    "WICKETKEEPER": "WK",
    "WICKET-KEEPER": "WK",
    "KEEPER": "WK",
    "BAT": "BAT",
    "BATTER": "BAT",
    "BATSMAN": "BAT",
    "AR": "AR",
    "ALL": "AR",
    "ALLROUNDER": "AR",
    "ALL-ROUNDER": "AR",
    "BOWL": "BOWL",
    "BOWLER": "BOWL",
}


@dataclass(frozen=True, slots=True)
class Candidate:
    id: str
    name: str
    team: str
    role: str
    points: float


@dataclass(frozen=True, slots=True)
class Pick:
    players: tuple[Candidate, ...]
    captain: Candidate
    vice: Candidate
    total: float


def normalise_role(raw: str | None) -> str | None:
    if not raw:
        return None
    key = re.sub(r"[\s_]", "", raw.strip().upper())
    return _ROLE_ALIASES.get(key) or _ROLE_ALIASES.get(key.replace("-", ""))


def best_xi(cands: Sequence[Candidate]) -> Pick | None:
    """Exact best XI under the role and per-team limits.

    For every feasible role split (wk, bat, ar, bowl) the best XI takes the top-k of each role;
    the per-team cap is checked and, if violated, that split is repaired greedily by swapping the
    weakest over-cap player for the best same-role player of the other side. C is the top scorer
    of the XI (x2), VC the second (x1.5).
    """
    by_role: dict[str, list[Candidate]] = {r: [] for r in ROLES}
    for c in cands:
        if c.role in by_role:
            by_role[c.role].append(c)
    for lst in by_role.values():
        lst.sort(key=lambda c: (-c.points, c.name))

    best: tuple[float, tuple[Candidate, ...]] | None = None
    ranges = [range(ROLE_MIN, min(ROLE_MAX, len(by_role[r])) + 1) for r in ROLES]
    for split in itertools.product(*ranges):
        if sum(split) != XI_SIZE:
            continue
        xi = [c for r, k in zip(ROLES, split, strict=True) for c in by_role[r][:k]]
        xi = _enforce_team_cap(xi, by_role)
        if xi is None:
            continue
        score = sum(c.points for c in xi)
        if best is None or score > best[0]:
            best = (score, tuple(xi))
    if best is None:
        return None
    ranked = sorted(best[1], key=lambda c: (-c.points, c.name))
    cap, vice = ranked[0], ranked[1]
    total = best[0] + cap.points + 0.5 * vice.points
    return Pick(players=best[1], captain=cap, vice=vice, total=round(total, 1))


def _enforce_team_cap(
    xi: list[Candidate], by_role: dict[str, list[Candidate]]
) -> list[Candidate] | None:
    xi = list(xi)
    for _ in range(XI_SIZE):
        counts: dict[str, int] = {}
        for c in xi:
            counts[c.team] = counts.get(c.team, 0) + 1
        over = [t for t, n in counts.items() if n > TEAM_MAX]
        if not over:
            return xi
        team = over[0]
        chosen = {c.id for c in xi}
        swaps = []
        for c in xi:
            if c.team != team:
                continue
            alt = next((a for a in by_role[c.role] if a.team != team and a.id not in chosen), None)
            if alt is not None:
                swaps.append((c.points - alt.points, c, alt))
        if not swaps:
            return None
        _, out, inn = min(swaps, key=lambda s: s[0])
        xi = [inn if c.id == out.id else c for c in xi]
    return None


def short_name(full: str) -> str:
    """'V Kohli' -> 'Kohli', 'Rashid Khan' stays, 'B Sai Sudharsan' -> 'Sai Sudharsan'."""
    parts = full.split()
    if len(parts) >= 2 and parts[0].isupper() and len(parts[0]) <= 3:
        return " ".join(parts[1:])
    return full


# --------------------------------------------------------------------------- runtime detection
def _columns(conn: Connection, table: str) -> set[str]:
    rows = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = :t"
        ),
        {"t": table},
    ).scalars()
    return set(rows)


def _pick(cols: set[str], options: Sequence[str]) -> str | None:
    return next((c for c in options if c in cols), None)


@dataclass(frozen=True, slots=True)
class XISource:
    points_col: str
    role_table: str  # "player_match_points" or "player_attribute"
    role_col: str
    attr_has_season: bool


def detect_source(conn: Connection) -> XISource | None:
    """Find usable points + role columns, or None if the persisted tables are not there yet."""
    pmp = _columns(conn, "player_match_points")
    if not {"match_id", "player_id"} <= pmp:
        return None
    points_col = _pick(pmp, _POINT_COLS)
    if points_col is None:
        return None
    role_col = _pick(pmp, _ROLE_COLS)
    if role_col is not None:
        return XISource(points_col, "player_match_points", role_col, False)
    attr = _columns(conn, "player_attribute")
    role_col = _pick(attr, _ROLE_COLS)
    if "player_id" not in attr or role_col is None:
        return None
    return XISource(points_col, "player_attribute", role_col, "season" in attr)


def load_candidates(conn: Connection, match_id: int, src: XISource) -> list[Candidate]:
    """Every player in the match XI (+ impact subs) with persisted points and a role."""
    if src.role_table == "player_match_points":
        role_join = ""
        role_expr = f"pmp.{src.role_col}"
    else:
        season_cond = " AND pa.season = s.year" if src.attr_has_season else ""
        role_join = f"LEFT JOIN player_attribute pa ON pa.player_id = pmp.player_id{season_cond}"
        role_expr = f"pa.{src.role_col}"
    sql = f"""
        SELECT pmp.player_id, p.name, mp.team_id, t.name AS team_name, s.year,
               {role_expr}::text AS role, pmp.{src.points_col}::float AS points
        FROM player_match_points pmp
        JOIN match m ON m.id = pmp.match_id
        JOIN season s ON s.id = m.season_id
        JOIN player p ON p.id = pmp.player_id
        JOIN match_player_resolved mp ON mp.match_id = pmp.match_id AND mp.player_id = pmp.player_id
        JOIN team t ON t.id = mp.team_id
        {role_join}
        WHERE pmp.match_id = :mid
    """  # noqa: S608 - identifiers come from a fixed allow-list above
    out: dict[str, Candidate] = {}
    for r in conn.execute(text(sql), {"mid": match_id}).mappings():
        role = normalise_role(r["role"])
        if role is None or r["points"] is None:
            continue
        out[r["player_id"]] = Candidate(
            id=r["player_id"],
            name=r["name"],
            team=team_code(r["team_name"], r["year"]),
            role=role,
            points=float(r["points"]),
        )
    return list(out.values())
