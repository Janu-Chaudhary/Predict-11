"""Pure-unit tests for the Dream11 scoring rule helpers."""
from predict11.scoring.fantasy_points import _band, _haul, _milestone, SR_BANDS, ECON_BANDS


def test_milestones_are_tiered_not_cumulative():
    assert _milestone(0) == 0
    assert _milestone(29) == 0
    assert _milestone(30) == 4
    assert _milestone(49) == 4
    assert _milestone(50) == 8
    assert _milestone(101) == 16  # century, not 4+8+16


def test_wicket_hauls():
    assert _haul(2) == 0
    assert _haul(3) == 4
    assert _haul(4) == 8
    assert _haul(5) == 16
    assert _haul(7) == 16  # capped at the 5-wicket tier


def test_strike_rate_bands():
    assert _band(180, SR_BANDS) == 6     # explosive
    assert _band(100, SR_BANDS) == 0     # neutral zone
    assert _band(40, SR_BANDS) == -6     # very slow


def test_economy_bands():
    assert _band(4.0, ECON_BANDS) == 6   # miserly
    assert _band(8.0, ECON_BANDS) == 0   # neutral
    assert _band(13.0, ECON_BANDS) == -6  # expensive
