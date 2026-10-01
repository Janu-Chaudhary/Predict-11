"""Check persisted points against 40 published IPL 2026 season-to-date Dream11 totals.

Cases are copied from ``spikes/scoring_check/check_totals.py`` (+ ``cases_extra.py``):
khelnow.com "Top 5 Dream11 fantasy picks" previews, each giving a player's season total
*before* the previewed match. ``cmp`` is "=" (exact) or ">" (article only says "over N").
The spike scored with hand-picked roles; here the totals come from ``player_match_points``
(resolved roles), so this also validates the attribute pipeline.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Connection, text

# (cricsheet name, role used by the spike, before date, published total, cmp, source)
CASES: tuple[tuple[str, str, str, int, str, str], ...] = (
    ("Shubman Gill", "BAT", "2026-05-31", 1522, "=", "khelnow rcb-vs-gt final"),
    ("RM Patidar", "BAT", "2026-05-31", 1066, "=", "khelnow rcb-vs-gt final"),
    ("V Kohli", "BAT", "2026-05-31", 1244, "=", "khelnow rcb-vs-gt final"),
    ("B Sai Sudharsan", "BAT", "2026-05-31", 1418, "=", "khelnow rcb-vs-gt final"),
    ("K Rabada", "BOWL", "2026-05-31", 1229, "=", "khelnow rcb-vs-gt final"),
    ("Abhishek Sharma", "AR", "2026-05-27", 1251, "=", "khelnow srh-vs-rr eliminator"),
    ("H Klaasen", "WK", "2026-05-27", 1238, "=", "khelnow srh-vs-rr eliminator"),
    ("Dhruv Jurel", "WK", "2026-05-27", 1060, "=", "khelnow srh-vs-rr eliminator"),
    ("B Sai Sudharsan", "BAT", "2026-05-29", 1250, ">", "khelnow gt-vs-rr q2"),
    ("Shubman Gill", "BAT", "2026-05-29", 1200, ">", "khelnow gt-vs-rr q2"),
    ("SP Narine", "AR", "2026-05-24", 745, "=", "khelnow kkr-vs-dc m70"),
    ("KL Rahul", "WK", "2026-05-24", 1081, "=", "khelnow kkr-vs-dc m70"),
    ("P Simran Singh", "WK", "2026-05-23", 929, "=", "khelnow lsg-vs-pbks m68"),
    ("C Connolly", "AR", "2026-05-23", 1000, ">", "khelnow lsg-vs-pbks m68"),
    ("V Suryavanshi", "BAT", "2026-05-24", 1277, "=", "khelnow mi-vs-rr m69"),
    ("Dhruv Jurel", "WK", "2026-05-24", 972, "=", "khelnow mi-vs-rr m69"),
    ("RD Rickelton", "WK", "2026-05-24", 982, "=", "khelnow mi-vs-rr m69"),
    ("Abhishek Sharma", "AR", "2026-05-18", 1063, "=", "khelnow csk-vs-srh m63"),
    ("SV Samson", "WK", "2026-05-18", 954, "=", "khelnow csk-vs-srh m63"),
    ("TM Head", "BAT", "2026-05-18", 757, "=", "khelnow csk-vs-srh m63"),
    ("MR Marsh", "AR", "2026-04-26", 418, "=", "khelnow lsg-vs-kkr m38"),
    ("RR Pant", "WK", "2026-04-26", 343, "=", "khelnow lsg-vs-kkr m38"),
    ("A Raghuvanshi", "BAT", "2026-04-26", 403, "=", "khelnow lsg-vs-kkr m38"),
    ("Shubman Gill", "BAT", "2026-05-03", 765, "=", "khelnow gt-vs-pbks m46"),
    ("P Simran Singh", "WK", "2026-05-03", 724, "=", "khelnow gt-vs-pbks m46"),
    ("Priyansh Arya", "BAT", "2026-05-03", 613, "=", "khelnow gt-vs-pbks m46"),
    ("SS Iyer", "BAT", "2026-05-03", 637, "=", "khelnow gt-vs-pbks m46"),
    ("P Simran Singh", "WK", "2026-04-28", 621, "=", "khelnow pbks-vs-rr m40"),
    ("YBK Jaiswal", "BAT", "2026-04-28", 537, "=", "khelnow pbks-vs-rr m40"),
    ("Priyansh Arya", "BAT", "2026-04-28", 544, "=", "khelnow pbks-vs-rr m40"),
    ("SS Iyer", "BAT", "2026-04-28", 581, "=", "khelnow pbks-vs-rr m40"),
    ("Mohsin Khan", "BOWL", "2026-05-04", 413, "=", "khelnow mi-vs-lsg m47"),
    ("Prince Yadav", "BOWL", "2026-05-04", 551, "=", "khelnow mi-vs-lsg m47"),
    ("Naman Dhir", "BAT", "2026-05-04", 499, "=", "khelnow mi-vs-lsg m47"),
    ("MR Marsh", "AR", "2026-05-04", 432, "=", "khelnow mi-vs-lsg m47"),
    ("B Kumar", "BOWL", "2026-05-13", 919, "=", "khelnow rcb-vs-kkr m57"),
    ("V Kohli", "BAT", "2026-05-13", 807, "=", "khelnow rcb-vs-kkr m57"),
    ("C Green", "AR", "2026-05-13", 626, "=", "khelnow rcb-vs-kkr m57"),
    ("KL Rahul", "WK", "2026-05-08", 921, "=", "khelnow dc-vs-kkr m51"),
    ("A Raghuvanshi", "BAT", "2026-05-08", 531, "=", "khelnow dc-vs-kkr m51"),
)

SQL = """
WITH pl AS (
  SELECT DISTINCT p.id FROM player p
  JOIN match_player_resolved mp ON mp.player_id = p.id
  JOIN match m ON m.id = mp.match_id JOIN season s ON s.id = m.season_id
  WHERE s.year = 2026 AND p.name = :name
)
SELECT count(DISTINCT pl.id) AS ids, coalesce(sum(x.total), 0) AS total,
       count(x.match_id) AS matches, max(x.role_used) AS role, min(x.role_used) AS role_min
FROM pl LEFT JOIN (
  SELECT pmp.* FROM player_match_points pmp JOIN match m ON m.id = pmp.match_id
  JOIN season s ON s.id = m.season_id
  WHERE s.year = 2026 AND m.start_date < CAST(:before AS date)
) x ON x.player_id = pl.id
"""


def validate_2026(conn: Connection) -> dict[str, Any]:
    results = []
    for name, spike_role, before, published, cmp, src in CASES:
        r = conn.execute(text(SQL), {"name": name, "before": before}).mappings().one()
        ours = int(r["total"])
        ok = r["ids"] == 1 and (ours == published if cmp == "=" else ours > published)
        results.append({
            "player": name, "before": before, "published": f"{cmp}{published}", "ours": ours,
            "matches": r["matches"], "role": r["role"], "spike_role": spike_role, "ok": ok,
            "source": src,
        })
    passed = sum(1 for x in results if x["ok"])
    return {"cases": len(results), "passed": passed,
            "failed": [x for x in results if not x["ok"]], "results": results}
