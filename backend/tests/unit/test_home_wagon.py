"""Hero A shot parsing and the documented dev fallback flag."""

from __future__ import annotations

import pytest

from p11.analytics import home_wagon as hw


def spider(**kw: object) -> dict[str, object]:
    base = {
        "batting_player_name": "V Kohli",
        "batting_player_hand": "right",
        "innings_number": 2,
        "over_number": 3,
        "ball_number": 1,
        "runs_off_bat": 4,
        "field_direction": 52,
        "field_distance_percent": 100,
        "field_zone": 1,
        "bowling_player_name": "M Siraj",
    }
    base.update(kw)
    return base


def test_parse_spider_converts_overs_and_skips_dots() -> None:
    shots = hw.parse_spider(
        {"spider_data": [spider(), spider(runs_off_bat=0), spider(over_number=1, ball_number=2)]}
    )
    assert [(s.over, s.ball) for s in shots] == [(0, 2), (2, 1)]
    assert not shots[0].left_handed


def test_top_innings_by_runs() -> None:
    shots = hw.parse_spider(
        {
            "spider_data": [
                spider(),
                spider(runs_off_bat=6),
                spider(batting_player_name="S Gill", innings_number=1, runs_off_bat=6),
            ]
        }
    )
    top = hw.top_innings(shots)
    assert top is not None and top[0] == "V Kohli" and top[1] == 10
    assert hw.top_innings([]) is None


def test_no_shot_data_without_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(hw.DEV_FLAG_ENV, raising=False)
    assert hw.load_shots(hw.SPIKE_FINAL_2026_MATCH_ID) is None
    assert hw.load_shots(1) is None


def test_dev_flag_serves_only_the_2026_final(monkeypatch: pytest.MonkeyPatch) -> None:
    if not hw.SPIKE_FILE.exists():
        pytest.skip("spike sample not present")
    monkeypatch.setenv(hw.DEV_FLAG_ENV, "1")
    shots = hw.load_shots(hw.SPIKE_FINAL_2026_MATCH_ID)
    assert shots is not None and len(shots) > 100
    top = hw.top_innings(shots)
    assert top is not None and top[0] == "V Kohli" and top[1] == 75
    assert hw.load_shots(1535464) is None
