"""D2 bowling-type / batting-hand splits and E1 venue extras (pure maths, no DB)."""

from __future__ import annotations

import datetime as dt

import pytest

from p11.analytics.conditions import (
    BOWLING_TYPES,
    group_of,
    pace_spin_window,
    split_by_hand,
    split_by_type,
    toss_season,
)
from p11.analytics.players_data import InningsTotal, MatchInfo, Reference
from p11.analytics.players_stats import Ball, BowlingCard
from p11.core.models import BOWLING_TYPES as MODEL_TYPES


def test_every_model_bowling_type_has_a_group() -> None:
    assert set(BOWLING_TYPES) == set(MODEL_TYPES)
    groups = {t: group_of(t) for t in MODEL_TYPES}
    assert {t for t, g in groups.items() if g == "pace"} == {
        "right-arm fast",
        "right-arm medium",
        "left-arm fast",
        "left-arm medium",
    }
    assert {t for t, g in groups.items() if g == "spin"} == {
        "off-spin",
        "leg-spin",
        "left-arm orthodox",
        "left-arm wrist",
    }
    assert group_of(None) is None and group_of("slow junk") is None


def _b(bowler: str, runs: int = 0, *, wide: int = 0, out: str | None = None, batter: str = "X"):
    return Ball(
        1,
        1,
        0,
        batter,
        bowler,
        "N",
        runs,
        wides=wide,
        wicket_kind=out,
        player_out=batter if out else None,
    )


def test_split_by_type_groups_and_unknown() -> None:
    types = {"fast1": "right-arm fast", "off1": "off-spin", "sla1": "left-arm orthodox"}
    balls = [
        _b("fast1", 4),
        _b("fast1", 0),
        _b("fast1", 0, wide=1),  # wide: not faced, not a dot
        _b("off1", 6),
        _b("off1", 0, out="caught"),
        _b("sla1", 1),
        _b("sla1", 0, out="run out"),  # not a bowler dismissal
        _b("mystery", 2),
    ]
    rows, groups, unknown, unknown_bowlers = split_by_type(balls, types)
    by = {r.bowling_type: r for r in rows}
    assert [r.bowling_type for r in rows] == list(BOWLING_TYPES)
    assert (by["right-arm fast"].balls, by["right-arm fast"].runs) == (2, 4)
    assert by["right-arm fast"].dot_pct == 50.0 and by["right-arm fast"].boundary_pct == 50.0
    assert by["off-spin"].dismissals == 1 and by["off-spin"].strike_rate == 300.0
    assert by["left-arm orthodox"].dismissals == 0
    assert by["leg-spin"].balls == 0 and by["leg-spin"].strike_rate is None
    g = {r.bowling_type: r for r in groups}
    assert (g["pace"].balls, g["spin"].balls) == (2, 4)
    assert g["spin"].runs == 7 and g["spin"].bowlers == 2
    assert unknown.balls == 1 and unknown_bowlers == {"mystery"}
    assert by["right-arm fast"].confidence == "low"


def test_split_by_hand() -> None:
    hands = {"R1": "R", "L1": "L"}
    balls = [
        _b("B", 4, batter="R1"),
        _b("B", 0, batter="R1"),
        _b("B", 0, batter="R1", out="bowled"),
        _b("B", 0, wide=1, batter="R1"),  # wide: 1 run conceded, not legal
        _b("B", 6, batter="L1"),
        _b("B", 1, batter="who"),
    ]
    rows, unknown = split_by_hand(balls, hands)
    r, lh = rows
    assert (r.label, r.balls, r.runs_conceded, r.wickets) == ("RHB", 3, 5, 1)
    assert r.economy == 10.0 and r.strike_rate == 3.0 and r.average == 5.0
    assert r.dot_pct == pytest.approx(66.67)
    assert (lh.label, lh.balls, lh.runs_conceded, lh.wickets, lh.strike_rate) == (
        "LHB",
        1,
        6,
        0,
        None,
    )
    assert lh.boundary_pct == 100.0
    assert unknown.balls == 1


def test_pace_spin_window_shares() -> None:
    types = {"p": "right-arm fast", "s": "leg-spin"}
    cards = [
        ("p", BowlingCard(1, 1, balls=24, runs=40, wickets=1)),
        ("s", BowlingCard(1, 1, balls=24, runs=20, wickets=2)),
        ("u", BowlingCard(1, 2, balls=12, runs=12, wickets=1)),
    ]
    w = pace_spin_window("recent", cards, types, matches=1)
    g = {x.group: x for x in w.groups}
    assert g["pace"].economy == 10.0 and g["spin"].economy == 5.0
    assert g["spin"].strike_rate == 12.0 and g["spin"].average == 10.0
    assert g["pace"].overs_share_pct == 40.0 and g["spin"].wickets_share_pct == 50.0
    assert w.unknown_ball_pct == 20.0
    t = {x.group: x for x in w.by_type}
    assert t["leg-spin"].balls == 24 and t["off-spin"].balls == 0


def _ref(rows: list[tuple]) -> tuple[Reference, dict[int, dict[int, InningsTotal]]]:
    """rows: (mid, toss_winner, decision, result, winner, method, chaser)."""
    matches, bt, inns = {}, {}, {}
    for mid, tw, dec, res, win, meth, chaser in rows:
        matches[mid] = MatchInfo(
            mid, dt.date(2024, 4, mid), 2024, 1, 10, 20, tw, dec, res, win, meth, None
        )
        first = 20 if chaser == 10 else 10
        bt[(mid, 1)], bt[(mid, 2)] = first, chaser
        inns[mid] = {
            1: InningsTotal(mid, 1, first, runs=180),
            2: InningsTotal(mid, 2, chaser, runs=170),
        }
    order = {m: i for i, m in enumerate(matches)}
    return Reference(matches, order, bt, [], {}, {1: ("V", None)}, {}), inns


def test_toss_season_maths() -> None:
    ref, inns = _ref(
        [
            (1, 10, "field", "win", 10, None, 10),  # toss winner fielded, chased, won
            (2, 20, "field", "win", 10, None, 20),  # toss winner fielded, chase lost
            (3, 10, "bat", "win", 10, None, 20),  # toss winner batted, won defending
            (4, 20, "field", "win", 20, "D/L", 20),  # DLS: counts for toss, not for chase
            (5, 10, "field", "no_result", None, None, 20),  # NR: field choice only
        ]
    )
    s = toss_season(ref, 2024, list(ref.matches), inns)
    assert s.matches == 5
    assert s.toss_field_pct == 80.0  # 4 of 5 decisions
    assert s.toss_winner_win_pct == 75.0  # 3 of 4 results (NR excluded)
    assert s.decided == 3 and s.chase_win_pct == pytest.approx(33.3)
