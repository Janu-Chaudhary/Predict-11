"""Data-quality report over what is stored (``p11 dq report``)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Connection, text


def dq_report(conn: Connection) -> dict[str, Any]:
    q = conn.execute
    status = dict(q(text("SELECT data_status, count(*) FROM match GROUP BY 1 ORDER BY 1")).all())
    sources = [
        dict(r._mapping)
        for r in q(
            text(
                "SELECT source, status, count(*) AS n FROM match_source GROUP BY 1, 2 ORDER BY 1, 2"
            )
        )
    ]
    payloads = dict(q(text("SELECT parse_status, count(*) FROM raw_payload GROUP BY 1")).all())
    quarantined = [
        {"match_id": r[0], "source": r[1], "date": str(r[2]), "issues": r[3]}
        for r in q(
            text(
                "SELECT ms.match_id, ms.source, m.start_date, ms.dq_issues FROM match_source ms "
                "JOIN match m ON m.id = ms.match_id WHERE ms.status = 'quarantined' "
                "ORDER BY m.start_date"
            )
        )
    ]
    by_season = [
        dict(r._mapping)
        for r in q(
            text(
                "SELECT s.year AS season, count(DISTINCT m.id) AS matches, "
                "(SELECT count(*) FROM delivery_resolved d JOIN match mm ON mm.id = d.match_id "
                " WHERE mm.season_id = s.id) AS deliveries "
                "FROM match m JOIN season s ON s.id = m.season_id GROUP BY s.id, s.year ORDER BY 1"
            )
        )
    ]
    # every player referenced by a resolved ball must be a registered player (FK-enforced; this
    # also catches match_player gaps: balls by someone not in that match's team sheet)
    orphan_balls = q(
        text(
            "SELECT count(*) FROM delivery_resolved d WHERE NOT EXISTS (SELECT 1 FROM "
            "match_player_resolved mp WHERE mp.match_id = d.match_id "
            "AND mp.player_id = d.batter_id)"
        )
    ).scalar_one()
    conflicts = q(text("SELECT count(*) FROM field_conflict WHERE status = 'open'")).scalar_one()
    totals = {
        t: q(text(f"SELECT count(*) FROM {t}")).scalar_one()
        for t in (
            "player",
            "player_source_id",
            "player_alias",
            "team",
            "venue",
            "match",
            "match_player",
            "delivery",
            "raw_payload",
            "season_credits",
        )
    }
    return {
        "totals": totals,
        "match_status": status,
        "source_copies": sources,
        "raw_payload_status": payloads,
        "open_field_conflicts": conflicts,
        "balls_with_batter_missing_from_team_sheet": orphan_balls,
        "by_season": by_season,
        "quarantined": quarantined,
    }
