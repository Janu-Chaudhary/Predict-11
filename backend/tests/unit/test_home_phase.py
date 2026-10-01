"""Home hero rotation rules (docs/DESIGN-DIRECTION.md §8)."""

from __future__ import annotations

import datetime as dt

import pytest

from p11.analytics.home import ball_kind
from p11.analytics.home_phase import (
    IST,
    choose_hero,
    decide_phase,
    match_title,
    overs_text,
    post_window_end,
)


def at(y: int, mo: int, d: int, h: int = 12, mi: int = 0) -> dt.datetime:
    return dt.datetime(y, mo, d, h, mi, tzinfo=IST)


def test_off_season_when_no_fixture_and_last_match_is_old() -> None:
    assert decide_phase(at(2026, 10, 2), None, dt.date(2026, 5, 31)) == "off_season"
    assert decide_phase(at(2026, 10, 2), None, None) == "off_season"


def test_post_match_shortly_after_last_match_without_fixture() -> None:
    assert decide_phase(at(2026, 6, 1, 9), None, dt.date(2026, 5, 31)) == "post_match"
    assert decide_phase(at(2026, 6, 2, 23), None, dt.date(2026, 5, 31)) == "post_match"
    assert decide_phase(at(2026, 6, 3, 0, 1), None, dt.date(2026, 5, 31)) == "off_season"


def test_fixture_known_is_pre_match_once_post_window_closes() -> None:
    nxt = at(2026, 4, 12, 19, 30)
    # the morning after a match, next fixture still > 8 h away: post-match
    assert decide_phase(at(2026, 4, 11, 9), nxt - dt.timedelta(days=1), dt.date(2026, 4, 10)) == (
        "post_match"
    )
    # after noon the next day: pre-match
    assert decide_phase(at(2026, 4, 11, 13), nxt, dt.date(2026, 4, 10)) == "pre_match"
    # within 8 h of the next start, pre-match wins even inside the post window
    assert decide_phase(at(2026, 4, 12, 11, 59), nxt, dt.date(2026, 4, 11)) == "pre_match"
    # first match of a season (no previous match)
    assert decide_phase(at(2026, 3, 1), nxt, None) == "pre_match"


def test_post_window_ends_noon_next_day() -> None:
    assert post_window_end(dt.date(2026, 5, 31)) == at(2026, 6, 1, 12)


def test_naive_now_rejected() -> None:
    with pytest.raises(ValueError):
        decide_phase(dt.datetime(2026, 1, 1), None, None)


@pytest.mark.parametrize(
    ("phase", "xi", "wagon", "hero"),
    [
        ("pre_match", True, False, "B"),
        ("pre_match", False, True, "C"),
        ("post_match", False, True, "A"),
        ("post_match", True, False, "C"),
        ("off_season", True, True, "C"),
    ],
)
def test_choose_hero(phase: str, xi: bool, wagon: bool, hero: str) -> None:
    got, reason = choose_hero(phase, xi_available=xi, wagon_available=wagon)  # type: ignore[arg-type]
    assert got == hero and reason


def test_overs_text_and_titles() -> None:
    assert overs_text(120) == "20"
    assert overs_text(107) == "17.5"
    assert overs_text(0) == "0"
    assert match_title("Final", None) == "Final"
    assert match_title(None, 41) == "Match 41"
    assert match_title(None, None) == "League match"


def test_ball_kind() -> None:
    assert ball_kind(0, 0, None) == "dot"
    assert ball_kind(0, 1, None) == "run"  # a wide still counts on the worm
    assert ball_kind(2, 2, None) == "run"
    assert ball_kind(4, 4, None) == "four"
    assert ball_kind(6, 6, None) == "six"
    assert ball_kind(0, 0, "caught") == "wicket"
    assert ball_kind(1, 1, "run out") == "wicket"
    assert ball_kind(0, 0, "retired hurt") == "dot"
