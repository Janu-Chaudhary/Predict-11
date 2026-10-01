"""Write parsed source copies of matches into Postgres (source-agnostic).

Each source writes only its own rows (``match_source``/``innings``/``match_player``/``delivery``
keyed by source). The shared ``match`` row is created by whichever source sees the match first
and refreshed by a source only while ``match.resolved_from`` is that source — once a vote or a
manual fix owns the row, source loaders no longer overwrite it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, text

from p11.core.upsert import ChangeLog, Changes, upsert
from p11.registry.canonical import Resolver

from .sources.cricsheet import ParsedMatch


@dataclass
class SourceCopy:
    """One parsed match from one source, plus provenance and DQ outcome."""

    parsed: ParsedMatch
    source: str
    source_match_key: str
    raw_payload_id: int | None
    issues: list[dict[str, Any]]

    @property
    def quarantined(self) -> bool:
        return bool(self.issues)

    @property
    def children_loadable(self) -> bool:
        # FKs need every player id to exist; with unresolved players we keep only the
        # match_source row (quarantined, with the issues) and skip balls/players.
        return not any(i["check"] == "registry" for i in self.issues)


def write_copies(conn: Connection, copies: list[SourceCopy], resolver: Resolver) -> ChangeLog:
    log = ChangeLog()
    if not copies:
        return log
    matches, sources, innings, players, balls = [], [], [], [], []
    scopes: list[tuple[int, str]] = []
    for c in copies:
        m = c.parsed
        t = {name: resolver.team(name) for name in m.teams}
        status = "quarantined" if c.quarantined else "single_source"
        matches.append(
            {
                "id": m.match_id,
                **(
                    {"cricsheet_id": m.match_id, "cricinfo_id": m.match_id}
                    if c.source == "cricsheet"
                    else {"cricsheet_id": None, "cricinfo_id": None}
                ),
                "season_id": resolver.season(m.event_name, m.season_year, m.season_label),
                "start_date": m.start_date,
                "venue_id": resolver.venue(m.venue, m.city) if m.venue else None,
                "city": m.city,
                "team1_id": t[m.teams[0]],
                "team2_id": t[m.teams[1]],
                "toss_winner_id": t.get(m.toss_winner) if m.toss_winner else None,
                "toss_decision": m.toss_decision,
                "result": m.result,
                "winner_id": t.get(m.winner) if m.winner else None,
                "win_by_runs": m.win_by_runs,
                "win_by_wickets": m.win_by_wickets,
                "method": m.method,
                "match_number": m.match_number,
                "stage": m.stage,
                "overs": m.overs,
                "player_of_match": m.player_of_match or None,
                "resolved_from": c.source,
                "ball_source": c.source,
                "data_status": status,
            }
        )
        sources.append(
            {
                "match_id": m.match_id,
                "source": c.source,
                "source_match_key": c.source_match_key,
                "raw_payload_id": c.raw_payload_id,
                "revision": m.revision,
                "status": "quarantined" if c.quarantined else "loaded",
                "dq_issues": c.issues or None,
                "facts": m.facts(),
            }
        )
        if not c.children_loadable:
            continue
        scopes.append((m.match_id, c.source))
        for i in m.innings:
            innings.append(
                {
                    "match_id": m.match_id,
                    "source": c.source,
                    "innings": i.innings,
                    "team_id": t[i.team],
                    "super_over": i.super_over,
                    "target_runs": i.target_runs,
                    "target_overs": i.target_overs,
                    "absent_hurt": i.absent_hurt or None,
                }
            )
        for p in m.players:
            players.append(
                {
                    "match_id": m.match_id,
                    "source": c.source,
                    "player_id": p["player_id"],
                    "team_id": t[p["team"]],
                    "role_in_match": p["role_in_match"],
                }
            )
        for d in m.deliveries:
            balls.append({"match_id": m.match_id, "source": c.source, **d})

    # match: refreshed by this source only while it is the resolver; data_status/ball_source are
    # owned by refresh_match_status / the merger and never overwritten here.
    src = copies[0].source
    owned = {"id", "data_status", "ball_source", "resolved_from"}
    if src != "cricsheet":
        owned |= {"cricsheet_id", "cricinfo_id"}
    upd = [k for k in matches[0] if k not in owned]
    log.add(
        "match",
        upsert(
            conn, "match", matches, ["id"], update=upd, update_where=f"t.resolved_from = '{src}'"
        ),
    )
    log.add("match_source", upsert(conn, "match_source", sources, ["match_id", "source"]))
    log.add(
        "innings",
        upsert(
            conn,
            "innings",
            innings,
            ["match_id", "source", "innings"],
            delete_missing=(["match_id", "source"], scopes),
        ),
    )
    log.add(
        "match_player",
        upsert(
            conn,
            "match_player",
            players,
            ["match_id", "source", "player_id"],
            delete_missing=(["match_id", "source"], scopes),
        ),
    )
    log.add(
        "delivery",
        upsert(
            conn,
            "delivery",
            balls,
            ["match_id", "source", "innings", "ball_seq"],
            delete_missing=(["match_id", "source"], scopes),
        ),
    )
    log.add("match", refresh_match_status(conn, [c.parsed.match_id for c in copies]))
    return log


def refresh_match_status(conn: Connection, match_ids: list[int]) -> Changes:
    """Derive match.data_status from its source copies and open conflicts."""
    n = conn.execute(
        text(
            """
            UPDATE match m SET data_status = s.new
            FROM (
              SELECT ms.match_id,
                CASE
                  WHEN count(*) FILTER (WHERE ms.status = 'loaded') = 0 THEN 'quarantined'
                  WHEN EXISTS (SELECT 1 FROM field_conflict fc
                               WHERE fc.match_id = ms.match_id AND fc.status = 'open')
                    THEN 'conflict'
                  WHEN count(*) FILTER (WHERE ms.status = 'loaded') = 1 THEN 'single_source'
                  WHEN bool_or(mm.data_status = 'verified') THEN 'verified'
                  ELSE 'unverified'
                END AS new
              FROM match_source ms JOIN match mm ON mm.id = ms.match_id
              WHERE ms.match_id = ANY(:ids)
              GROUP BY ms.match_id
            ) s
            WHERE m.id = s.match_id AND m.data_status IS DISTINCT FROM s.new
            """
        ),
        {"ids": match_ids},
    ).rowcount
    return Changes(updated=n)
