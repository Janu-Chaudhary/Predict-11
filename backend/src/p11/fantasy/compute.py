"""Persist Dream11 fantasy points per (match, player) into ``player_match_points``.

Inputs: resolved deliveries + lineups (``delivery_resolved`` / ``match_player_resolved``), the
resolved playing role (``player_attribute_resolved``; AR when a player has none) and the rule
set in force on the match date. Dream11 rule sets are only known from 2024 (RULES.md), so every
older match is scored with the oldest set, ``T20_2024`` (an approximation: pre-2024 IPL scoring
differed). No-result matches are stored with 0 for everyone.

Lineup status mapping (``match_player.role_in_match`` -> scorer):
  xi, impact_out -> STARTING_XI (the subbed-out player keeps his +4 and contributions)
  impact_in, sub (concussion replacement) -> SUBSTITUTE_PLAYED
  sub_fielder -> not scored (ordinary substitute fielders earn nothing)

Idempotent: rows are merged with IS DISTINCT FROM, so a re-run writes nothing; without
``force`` only matches with missing or stale rows (rule version or role changed) are scored.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import Connection, text

from p11.core.upsert import Changes, upsert
from p11.scoring import (
    T20_2024,
    Delivery,
    LineupEntry,
    LineupStatus,
    Role,
    RuleSet,
    ruleset_for_date,
    score_match,
)

DEFAULT_ROLE = Role.AR
STATUS_MAP = {
    "xi": LineupStatus.STARTING_XI,
    "impact_out": LineupStatus.STARTING_XI,
    "impact_in": LineupStatus.SUBSTITUTE_PLAYED,
    "sub": LineupStatus.SUBSTITUTE_PLAYED,
}
EXTRA_COLS = ("wides", "noballs", "byes", "legbyes", "penalty")
VALUE_COLS = ("team_id", "rules_version", "role_used", "role_source", "status", "batting",
              "bowling", "fielding", "lineup", "bonuses", "total", "items")


def rules_for(d: date) -> RuleSet:
    """Rule set in force on ``d``; the oldest known set (T20_2024) before it existed."""
    return ruleset_for_date(d) if d >= T20_2024.effective_from else T20_2024


@dataclass
class ComputeReport:
    matches_in_scope: int = 0
    matches_scored: int = 0
    rows: int = 0
    no_result_matches: int = 0
    default_roles: int = 0
    warnings: list[str] = field(default_factory=list)
    changes: Changes = field(default_factory=Changes)
    seconds: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        d = dict(vars(self))
        d["changes"] = vars(self.changes)
        d["warnings"] = self.warnings[:20]
        return d


def _scope(conn: Connection, seasons: Sequence[int] | None) -> list[dict[str, Any]]:
    sql = """
        SELECT m.id, m.start_date, m.result, s.year
        FROM match m JOIN season s ON s.id = m.season_id
        JOIN competition c ON c.id = s.competition_id
        WHERE c.code = 'ipl' {extra}
        ORDER BY m.start_date, m.id
    """
    if seasons:
        return [dict(r) for r in conn.execute(
            text(sql.format(extra="AND s.year = ANY(:ys)")), {"ys": list(seasons)}).mappings()]
    return [dict(r) for r in conn.execute(text(sql.format(extra=""))).mappings()]


def _stale(conn: Connection, ids: list[int]) -> set[int]:
    """Matches with no rows, or rows whose role no longer matches the resolved role."""
    rows = conn.execute(
        text(
            """
            SELECT m.id FROM unnest(CAST(:ids AS bigint[])) AS m(id)
            WHERE NOT EXISTS (SELECT 1 FROM player_match_points p WHERE p.match_id = m.id)
               OR EXISTS (
                 SELECT 1 FROM player_match_points p
                 LEFT JOIN player_attribute_resolved r USING (player_id)
                 WHERE p.match_id = m.id
                   AND p.role_used IS DISTINCT FROM coalesce(r.playing_role, :dflt))
               OR EXISTS (
                 SELECT 1 FROM match_player_resolved mp
                 WHERE mp.match_id = m.id
                   AND mp.role_in_match IN ('xi', 'impact_in', 'impact_out', 'sub')
                   AND NOT EXISTS (SELECT 1 FROM player_match_points p
                                   WHERE p.match_id = m.id AND p.player_id = mp.player_id))
            """
        ),
        {"ids": ids, "dflt": DEFAULT_ROLE.value},
    )
    return {r[0] for r in rows}


def _load_inputs(conn: Connection, ids: list[int]):
    deliveries: dict[int, list[Delivery]] = defaultdict(list)
    for r in conn.execute(
        text(
            """
            SELECT match_id, innings, over, ball_in_over, super_over, batter_id, bowler_id,
                   non_striker_id, batter_runs, extras, extra_type, wides, noballs, byes,
                   legbyes, penalty, non_boundary, wicket_kind, player_out_id, fielder_ids
            FROM delivery_resolved WHERE match_id = ANY(:ids)
            ORDER BY match_id, innings, ball_seq
            """
        ),
        {"ids": ids},
    ).mappings():
        comp = {k: r[k] for k in EXTRA_COLS if r[k]}
        deliveries[r["match_id"]].append(
            Delivery(
                innings=r["innings"],
                over=r["over"],
                ball=r["ball_in_over"],
                batter=r["batter_id"],
                bowler=r["bowler_id"],
                non_striker=r["non_striker_id"],
                batter_runs=r["batter_runs"],
                extras=r["extras"],
                extra_type=r["extra_type"],
                extras_detail=comp if len(comp) > 1 else None,
                super_over=r["super_over"],
                wicket_kind=r["wicket_kind"],
                player_out=r["player_out_id"],
                fielders=tuple(r["fielder_ids"] or ()),
                is_boundary=False if r["non_boundary"] else None,
            )
        )
    lineups: dict[int, list[tuple[str, int, str, str | None, str | None]]] = defaultdict(list)
    for r in conn.execute(
        text(
            """
            SELECT mp.match_id, mp.player_id, mp.team_id, mp.role_in_match,
                   ra.playing_role, ra.role_source
            FROM match_player_resolved mp
            LEFT JOIN player_attribute_resolved ra USING (player_id)
            WHERE mp.match_id = ANY(:ids)
              AND mp.role_in_match IN ('xi', 'impact_in', 'impact_out', 'sub')
            ORDER BY mp.match_id, mp.player_id
            """
        ),
        {"ids": ids},
    ):
        lineups[r[0]].append((r[1], r[2], r[3], r[4], r[5]))
    return deliveries, lineups


def score_matches(conn: Connection, matches: list[dict[str, Any]], rep: ComputeReport):
    ids = [m["id"] for m in matches]
    deliveries, lineups = _load_inputs(conn, ids)
    out: list[dict[str, Any]] = []
    for m in matches:
        rules = rules_for(m["start_date"])
        no_result = m["result"] == "no_result"
        rep.no_result_matches += no_result
        entries, meta = [], {}
        for pid, team_id, status, role, role_src in lineups.get(m["id"], []):
            if role is None:
                rep.default_roles += 1
            r = Role(role) if role else DEFAULT_ROLE
            entries.append(LineupEntry(pid, str(team_id), r, STATUS_MAP[status]))
            meta[pid] = (team_id, status, r.value, role_src or "default")
        ms = score_match(deliveries.get(m["id"], []), entries, rules, no_result=no_result)
        rep.warnings += [f"{m['id']}: {w}" for w in ms.warnings]
        for pid, ps in ms.players.items():
            team_id, status, role, role_src = meta[pid]
            out.append({
                "match_id": m["id"], "player_id": pid, "team_id": team_id,
                "rules_version": ms.rules_version, "role_used": role, "role_source": role_src,
                "status": status, "batting": ps.batting, "bowling": ps.bowling,
                "fielding": ps.fielding, "lineup": ps.lineup, "bonuses": ps.bonuses,
                "total": ps.total, "items": {k: v for k, v in ps.items.items() if v},
            })
        rep.matches_scored += 1
    return out


def compute_points(
    conn: Connection, seasons: Sequence[int] | None = None, *, force: bool = False,
    batch: int = 200,
) -> ComputeReport:
    t0 = time.monotonic()
    rep = ComputeReport()
    scope = _scope(conn, seasons)
    rep.matches_in_scope = len(scope)
    if not force and scope:
        stale = _stale(conn, [m["id"] for m in scope])
        scope = [m for m in scope if m["id"] in stale]
    for i in range(0, len(scope), batch):
        chunk = scope[i : i + batch]
        rows = score_matches(conn, chunk, rep)
        rep.rows += len(rows)
        rep.changes += upsert(
            conn, "player_match_points", rows, ["match_id", "player_id"],
            update=list(VALUE_COLS),
            delete_missing=(["match_id"], [(m["id"],) for m in chunk]),
        )
    rep.seconds = round(time.monotonic() - t0, 2)
    return rep
