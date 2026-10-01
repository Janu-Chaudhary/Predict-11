"""Postgres -> Parquet lake (data/lake/) for DuckDB analytics/training.

Exports the *resolved* copy of every match (views ``*_resolved``) with ``data_status`` so
consumers can drop quarantined matches: ``WHERE data_status <> 'quarantined'``.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import Engine, text

QUERIES: dict[str, str] = {
    "matches": """
        SELECT m.id AS match_id, c.code AS competition, s.year AS season, s.label AS season_label,
               m.start_date, m.match_number, m.stage, v.name AS venue, m.city,
               t1.name AS team1, t2.name AS team2, tw.name AS toss_winner, m.toss_decision,
               m.result, w.name AS winner, m.win_by_runs, m.win_by_wickets, m.method, m.overs,
               m.player_of_match, m.data_status, m.resolved_from, m.ball_source
        FROM match m
        JOIN season s ON s.id = m.season_id JOIN competition c ON c.id = s.competition_id
        LEFT JOIN venue v ON v.id = m.venue_id
        JOIN team t1 ON t1.id = m.team1_id JOIN team t2 ON t2.id = m.team2_id
        LEFT JOIN team tw ON tw.id = m.toss_winner_id LEFT JOIN team w ON w.id = m.winner_id
        ORDER BY m.start_date, m.id
    """,
    "deliveries": """
        SELECT d.match_id, s.year AS season, m.start_date, d.innings, d.super_over, d.ball_seq,
               d.over, d.ball_in_over, bt.name AS batting_team, d.batter_id, d.bowler_id,
               d.non_striker_id, d.batter_runs, d.extras, d.total_runs, d.extra_type, d.wides,
               d.noballs, d.byes, d.legbyes, d.penalty, d.non_boundary, d.wicket_kind,
               d.player_out_id, d.fielder_ids, d.source, m.data_status
        FROM delivery_resolved d
        JOIN match m ON m.id = d.match_id JOIN season s ON s.id = m.season_id
        JOIN innings_resolved i ON i.match_id = d.match_id AND i.innings = d.innings
        JOIN team bt ON bt.id = i.team_id
        ORDER BY m.start_date, d.match_id, d.innings, d.ball_seq
    """,
    "match_players": """
        SELECT mp.match_id, s.year AS season, m.start_date, t.name AS team, mp.player_id,
               p.name AS player_name, mp.role_in_match, mp.source, m.data_status
        FROM match_player_resolved mp
        JOIN match m ON m.id = mp.match_id JOIN season s ON s.id = m.season_id
        JOIN team t ON t.id = mp.team_id JOIN player p ON p.id = mp.player_id
        ORDER BY m.start_date, mp.match_id, t.name, mp.player_id
    """,
    "players": """
        SELECT p.id AS player_id, p.name, p.unique_name,
               (SELECT min(source_key) FROM player_source_id x
                 WHERE x.player_id = p.id AND x.source = 'cricinfo') AS cricinfo_id
        FROM player p
        WHERE EXISTS (SELECT 1 FROM match_player mp WHERE mp.player_id = p.id)
        ORDER BY p.id
    """,
}


def export_lake(engine: Engine, lake_dir: Path) -> dict[str, int]:
    lake_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with engine.connect() as conn:
        for name, sql in QUERIES.items():
            res = conn.execute(text(sql))
            cols = list(res.keys())
            rows = res.all()
            table = pa.table({c: [r[i] for r in rows] for i, c in enumerate(cols)})
            tmp = lake_dir / f".{name}.parquet.part"
            pq.write_table(table, tmp, compression="zstd")
            tmp.replace(lake_dir / f"{name}.parquet")
            counts[name] = table.num_rows
    return counts
