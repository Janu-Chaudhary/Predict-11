"""Cricsheet JSON parsing + DQ checks on real IPL 2026 payloads (tests/fixtures/cricsheet)."""

from __future__ import annotations

import copy
import json
import re
from decimal import Decimal

import pytest

from p11.ingest.quality import check_match
from p11.ingest.sources.cricsheet import parse_bytes, parse_match
from tests.fixtures import DLS, FINAL, NO_RESULT, SUPER_OVER, cricsheet_json

HEX8 = re.compile(r"^[0-9a-f]{8}$")


def doc(mid: int) -> dict:
    return json.loads(cricsheet_json(mid))


def totals(m) -> dict[int, int]:
    out: dict[int, int] = {}
    for d in m.deliveries:
        out[d["innings"]] = out.get(d["innings"], 0) + d["total_runs"]
    return out


@pytest.mark.parametrize("mid", [FINAL, SUPER_OVER, DLS, NO_RESULT])
def test_real_payloads_pass_dq_and_use_registry_ids_only(mid):
    m = parse_bytes(cricsheet_json(mid), mid)
    assert check_match(m) == []
    assert not m.unresolved_names
    ids = {p["player_id"] for p in m.players}
    for d in m.deliveries:
        for col in ("batter_id", "bowler_id", "non_striker_id"):
            assert HEX8.match(d[col]) and d[col] in ids
        for f in d["fielder_ids"] or []:
            assert HEX8.match(f)
    seqs = [(d["innings"], d["ball_seq"]) for d in m.deliveries]
    assert len(seqs) == len(set(seqs))


def test_final():
    m = parse_bytes(cricsheet_json(FINAL), FINAL)
    assert m.stage == "Final" and m.season_year == 2026 and m.season_label == "2026"
    assert m.result == "win" and m.winner == "Royal Challengers Bengaluru"
    assert m.win_by_wickets == 5 and m.win_by_runs is None and m.method is None
    assert len(m.innings) == 2 and not any(i.super_over for i in m.innings)
    t = totals(m)
    assert m.innings[1].target_runs == t[1] + 1
    assert t[2] >= m.innings[1].target_runs
    roles = [p["role_in_match"] for p in m.players]
    assert roles.count("impact_in") == 2 and roles.count("impact_out") == 2
    assert all(len(v) == 12 for v in m.team_players.values())
    # Kohli is resolved through info.registry.people, not by name lookup
    assert "ba607b88" in {p["player_id"] for p in m.players}


def test_super_over_tie():
    m = parse_bytes(cricsheet_json(SUPER_OVER), SUPER_OVER)
    assert [i.super_over for i in m.innings] == [False, False, True, True]
    assert m.result == "tie" and m.winner == "Kolkata Knight Riders"  # super-over winner
    t = totals(m)
    assert t[1] == t[2]
    so = [d for d in m.deliveries if d["super_over"]]
    assert so and {d["innings"] for d in so} == {3, 4} and all(d["over"] == 0 for d in so)


def test_dls():
    m = parse_bytes(cricsheet_json(DLS), DLS)
    assert m.method == "D/L" and m.win_by_runs == 9
    assert m.innings[1].target_runs == 213 and m.innings[1].target_overs == Decimal("19")
    assert totals(m)[1] + 1 != 213  # revised target: plain target check must not apply


def test_no_result():
    m = parse_bytes(cricsheet_json(NO_RESULT), NO_RESULT)
    assert m.result == "no_result" and m.winner is None
    assert len(m.innings) == 1


def test_extras_are_split_by_kind():
    m = parse_bytes(cricsheet_json(SUPER_OVER), SUPER_OVER)
    wide = next(d for d in m.deliveries if d["wides"])
    assert wide["extra_type"] == "wides" and wide["extras"] == wide["wides"] + wide["noballs"]


# --------------------------------------------------------------------------- DQ fires
def _checks(d: dict) -> set[str]:
    return {i["check"] for i in check_match(parse_match(d, 1))}


def test_dq_ball_runs():
    d = doc(FINAL)
    d["innings"][0]["overs"][2]["deliveries"][0]["runs"]["batter"] += 4
    assert "ball_runs" in _checks(d)


def test_dq_target_vs_total():
    d = doc(FINAL)
    d["innings"][1]["target"]["runs"] += 3
    assert "totals" in _checks(d)


def test_dq_too_many_overs():
    d = doc(FINAL)
    extra = copy.deepcopy(d["innings"][0]["overs"][-1])
    extra["over"] = 20
    d["innings"][0]["overs"].append(extra)
    assert "overs" in _checks(d)


def test_dq_too_many_wickets():
    d = doc(FINAL)
    inn = d["innings"][0]
    batter = inn["overs"][0]["deliveries"][0]["batter"]
    for o in inn["overs"]:
        for b in o["deliveries"]:
            b.setdefault("wickets", [{"player_out": batter, "kind": "bowled"}])
    assert "wickets" in _checks(d)


def test_dq_retired_hurt_is_not_a_wicket():
    d = doc(FINAL)
    b = d["innings"][0]["overs"][0]["deliveries"][0]
    b["wickets"] = [{"player_out": b["batter"], "kind": "retired hurt"}]
    m = parse_match(d, 1)
    assert "wickets" not in {i["check"] for i in check_match(m)}


def test_dq_player_count_and_unresolved_name():
    d = doc(FINAL)
    team = d["info"]["teams"][0]
    d["info"]["players"][team] = d["info"]["players"][team][:10]
    d["innings"][0]["overs"][0]["deliveries"][0]["batter"] = "Nobody Known"
    checks = _checks(d)
    assert {"players", "registry", "sides"} <= checks


def test_dq_unknown_registry_id():
    m = parse_bytes(cricsheet_json(FINAL), FINAL)
    known = {p["player_id"] for p in m.players}
    known.discard("ba607b88")
    issues = check_match(m, known)
    assert any(i["check"] == "registry" and "ba607b88" in i["detail"] for i in issues)
