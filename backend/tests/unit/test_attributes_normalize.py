"""Bowling-style / batting-hand / role normalisation and the history-based role fallback."""

from __future__ import annotations

import pytest

from p11.registry.attributes import (
    BOWLING_TYPES,
    CareerLine,
    derive_role,
    normalize_batting_hand,
    normalize_bowling_type,
    normalize_role,
    resolve,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # ESPNcricinfo long wording
        ("right-arm fast", "right-arm fast"),
        ("right-arm fast-medium", "right-arm fast"),
        ("right-arm medium-fast", "right-arm medium"),
        ("right-arm medium", "right-arm medium"),
        ("right-arm slow-medium", "right-arm medium"),
        ("right-arm offbreak", "off-spin"),
        ("legbreak", "leg-spin"),
        ("legbreak googly", "leg-spin"),
        ("slow left-arm orthodox", "left-arm orthodox"),
        ("left-arm wrist-spin", "left-arm wrist"),
        ("left-arm fast", "left-arm fast"),
        ("left-arm fast-medium", "left-arm fast"),
        ("left-arm medium-fast", "left-arm medium"),
        ("left-arm medium", "left-arm medium"),
        # Cricbuzz wording
        ("Right-arm legbreak", "leg-spin"),
        ("Left-arm orthodox", "left-arm orthodox"),
        ("Left-arm chinaman", "left-arm wrist"),
        ("Right-arm medium fast", "right-arm medium"),
        # BCCI / ESPN short codes
        ("SLA", "left-arm orthodox"),
        ("RFM", "right-arm fast"),
        ("RMF", "right-arm medium"),
        ("OB", "off-spin"),
        ("LBG", "leg-spin"),
        ("SLW", "left-arm wrist"),
        ("lws", "left-arm wrist"),
        ("LFM", "left-arm fast"),
        # unknown / empty
        ("", None),
        (None, None),
        ("right-arm bowler", None),
    ],
)
def test_normalize_bowling_type(raw, expected):
    assert normalize_bowling_type(raw) == expected
    if expected is not None:
        assert expected in BOWLING_TYPES


def test_multiple_styles_use_the_primary_one():
    assert normalize_bowling_type(["right-arm offbreak", "legbreak"]) == "off-spin"
    assert normalize_bowling_type(["", "legbreak googly"]) == "leg-spin"
    assert normalize_bowling_type("right-arm medium, right-arm offbreak") == "right-arm medium"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("right-hand bat", "R"), ("Left-hand bat", "L"), ("rhb", "R"), ("left", "L"),
     (["left-hand bat"], "L"), ("", None), (None, None)],
)
def test_normalize_batting_hand(raw, expected):
    assert normalize_batting_hand(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("wicketkeeper batter", "WK"), ("WK-Batsman", "WK"), ("WK-Batter", "WK"),
        ("wicketkeeper", "WK"), ("top-order batter", "BAT"), ("batsman", "BAT"),
        ("Batter", "BAT"), ("opening batter", "BAT"), ("bowling allrounder", "AR"),
        ("Batting Allrounder", "AR"), ("All-Rounder", "AR"), ("allrounder", "AR"),
        ("bowler", "BOWL"), ("Bowler", "BOWL"), ("undefined", None), ("", None),
        ([], None), (["middle-order batter"], "BAT"),
    ],
)
def test_normalize_role(raw, expected):
    assert normalize_role(raw) == expected


def test_keeper_flag_wins():
    assert normalize_role("batsman", keeper=True) == "WK"


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (CareerLine(matches=0, balls_faced=0, legal_balls_bowled=0), None),
        (CareerLine(50, 1200, 0, stumpings=3), "WK"),  # any stumping -> keeper
        (CareerLine(100, 2500, 30), "BAT"),  # part-timer: < 1 ball a match
        (CareerLine(80, 150, 1700), "BOWL"),  # ~21 balls bowled, 2 faced a match
        (CareerLine(60, 900, 1200), "AR"),  # 20 bowled + 15 faced a match
        (CareerLine(40, 300, 360), "BOWL"),  # 9 bowled but only 7.5 faced a match
        (CareerLine(40, 600, 360), "AR"),  # 9 bowled + 15 faced a match
    ],
)
def test_derive_role(line, expected):
    assert derive_role(line) == expected


def test_derive_role_rarely_used_bowler():
    # 10 games, bowled 1 over in total, never really batted -> bowler who was under-used
    assert derive_role(CareerLine(10, 5, 6)) == "BOWL"
    assert derive_role(CareerLine(10, 60, 6)) == "BAT"


def test_resolve_priority():
    rows = [
        {"source": "derived", "playing_role": "BOWL", "batting_hand": None},
        {"source": "cricinfo", "playing_role": "AR", "batting_hand": "L"},
        {"source": "bcci", "playing_role": "BAT", "batting_hand": "R"},
    ]
    assert resolve(rows, "playing_role") == ("BAT", "bcci")  # official squads decide role
    assert resolve(rows, "batting_hand") == ("L", "cricinfo")  # ESPN decides styles
    assert resolve(rows[:1], "batting_hand") == (None, None)
