"""Per-match data-quality checks on a parsed match (source-agnostic).

Any issue => the source copy is stored but marked ``quarantined`` with the issues listed; it is
never silently dropped. Checks:
  registry      every name maps to a registry id, and that id exists in ``player``
  teams         two teams; innings teams are among them
  overs         regular innings <= match overs (20), <= balls_per_over legal balls per over
                (unless Cricsheet flags miscounted_overs); super over <= 1 over
  wickets       regular innings <= 10, super over <= 2 (retired hurt/not out excluded)
  ball_runs     batter + extras == total on every ball; extras == sum of extra kinds
  multi_wicket  more than one wicket on a ball (schema stores one)
  players       11..13 per team and exactly 11 + match replacements (impact/concussion)
  sides         batters/non-strikers belong to the batting team, bowlers to the fielding team
  totals        non-DLS: target == first-innings total + 1; win-by-runs margin and
                win-by-wickets wickets/target agree with the ball-by-ball sums
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .sources.cricsheet import NOT_OUT_KINDS, ParsedMatch

Issue = dict[str, Any]


def _issue(check: str, detail: str, innings: int | None = None) -> Issue:
    return {"check": check, "innings": innings, "detail": detail}


def check_match(m: ParsedMatch, known_player_ids: set[str] | None = None) -> list[Issue]:
    issues: list[Issue] = []

    # registry ----------------------------------------------------------------------
    for n in sorted(m.unresolved_names):
        issues.append(_issue("registry", f"name not in info.registry.people: {n!r}"))
    if known_player_ids is not None:
        ids = {p["player_id"] for p in m.players}
        for d in m.deliveries:
            ids.update((d["batter_id"], d["bowler_id"], d["non_striker_id"]))
            if d["player_out_id"]:
                ids.add(d["player_out_id"])
            ids.update(d["fielder_ids"] or [])
        missing = sorted(i for i in ids if not i.startswith("?") and i not in known_player_ids)
        for i in missing:
            issues.append(_issue("registry", f"player id {i} not in player table"))

    # teams -------------------------------------------------------------------------
    if len(m.teams) != 2 or len(set(m.teams)) != 2:
        issues.append(_issue("teams", f"expected 2 distinct teams, got {m.teams}"))
    for inn in m.innings:
        if inn.team not in m.teams:
            issues.append(_issue("teams", f"batting team {inn.team!r} not in teams", inn.innings))

    # per-innings aggregates ----------------------------------------------------------
    by_inn: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for d in m.deliveries:
        by_inn[d["innings"]].append(d)
    totals: dict[int, int] = {}
    wkts: dict[int, int] = {}
    for inn in m.innings:
        balls = by_inn.get(inn.innings, [])
        totals[inn.innings] = sum(d["total_runs"] for d in balls)
        wkts[inn.innings] = sum(
            1 for d in balls if d["wicket_kind"] and d["wicket_kind"] not in NOT_OUT_KINDS
        )
        overs = {d["over"] for d in balls}
        max_overs, max_wk = (1, 2) if inn.super_over else (m.overs, 10)
        if overs and (len(overs) > max_overs or max(overs) >= max_overs):
            issues.append(
                _issue(
                    "overs",
                    f"{len(overs)} overs (max index {max(overs)}) > {max_overs}",
                    inn.innings,
                )
            )
        if not inn.miscounted_overs:
            legal: dict[int, int] = defaultdict(int)
            for d in balls:
                if not d["wides"] and not d["noballs"]:
                    legal[d["over"]] += 1
            bad = {o: n for o, n in legal.items() if n > m.balls_per_over}
            if bad:
                issues.append(
                    _issue(
                        "overs", f"overs with >{m.balls_per_over} legal balls: {bad}", inn.innings
                    )
                )
        if wkts[inn.innings] > max_wk:
            issues.append(_issue("wickets", f"{wkts[inn.innings]} wickets > {max_wk}", inn.innings))

    for d in m.deliveries:
        where = f"ball {d['innings']}/{d['ball_seq']} ({d['over']}.{d['ball_in_over']})"
        if d["batter_runs"] + d["extras"] != d["total_runs"]:
            issues.append(_issue("ball_runs", f"{where}: batter+extras != total", d["innings"]))
        parts = d["wides"] + d["noballs"] + d["byes"] + d["legbyes"] + d["penalty"]
        if parts != d["extras"]:
            issues.append(
                _issue("ball_runs", f"{where}: extras {d['extras']} != parts {parts}", d["innings"])
            )
    for inn_no, seq in m.multi_wicket_balls:
        issues.append(_issue("multi_wicket", f"ball {inn_no}/{seq} has >1 wicket", inn_no))

    # players -----------------------------------------------------------------------
    for t, ids in m.team_players.items():
        n, ins = len(ids), m.impact_ins.get(t, 0)
        if not 11 <= n <= 13 or n != 11 + ins:
            issues.append(_issue("players", f"{t}: {n} players listed, {ins} replacements in"))

    team_of = {p["player_id"]: p["team"] for p in m.players}
    inn_team = {i.innings: i.team for i in m.innings}
    wrong: dict[str, set[str]] = defaultdict(set)
    for d in m.deliveries:
        bat = inn_team.get(d["innings"])
        for col in ("batter_id", "non_striker_id"):
            if team_of.get(d[col]) != bat:
                wrong[f"{col} not in batting XI (innings {d['innings']})"].add(d[col])
        if team_of.get(d["bowler_id"]) == bat:
            wrong[f"bowler from batting side (innings {d['innings']})"].add(d["bowler_id"])
    for what, ids in wrong.items():
        issues.append(_issue("sides", f"{what}: {sorted(ids)}"))

    # totals vs result -----------------------------------------------------------------
    regular = [i for i in m.innings if not i.super_over]
    if m.method is None and len(regular) >= 2:
        first, second = regular[0], regular[1]
        t1, t2 = totals[first.innings], totals[second.innings]
        if second.target_runs is not None and second.target_runs != t1 + 1:
            issues.append(
                _issue(
                    "totals",
                    f"target {second.target_runs} != innings-1 total {t1} + 1",
                    second.innings,
                )
            )
        if m.result == "win" and m.win_by_runs is not None and t1 - t2 != m.win_by_runs:
            issues.append(_issue("totals", f"won by {m.win_by_runs} runs but totals {t1} v {t2}"))
        if m.result == "win" and m.win_by_wickets is not None:
            lost = wkts[second.innings]
            if m.winner != second.team or 10 - lost != m.win_by_wickets:
                issues.append(
                    _issue(
                        "totals",
                        f"won by {m.win_by_wickets} wkts but chasing side lost {lost}",
                        second.innings,
                    )
                )
            if second.target_runs is not None and t2 < second.target_runs:
                issues.append(
                    _issue("totals", f"chase {t2} < target {second.target_runs}", second.innings)
                )
        if m.result == "tie" and t1 != t2:
            issues.append(_issue("totals", f"tie but totals {t1} v {t2}"))
    return issues
