"""Rule set chosen for persisted points by match date."""

from __future__ import annotations

from datetime import date

from p11.fantasy.compute import STATUS_MAP, rules_for
from p11.scoring import T20_2024, T20_2025, T20_2026, LineupStatus


def test_rules_for_dates():
    assert rules_for(date(2008, 4, 18)) is T20_2024  # oldest known set as approximation
    assert rules_for(date(2024, 5, 26)) is T20_2024
    assert rules_for(date(2025, 3, 22)) is T20_2025
    assert rules_for(date(2026, 5, 31)) is T20_2026


def test_status_map():
    assert STATUS_MAP["impact_out"] is LineupStatus.STARTING_XI
    assert STATUS_MAP["impact_in"] is LineupStatus.SUBSTITUTE_PLAYED
    assert STATUS_MAP["sub"] is LineupStatus.SUBSTITUTE_PLAYED
    assert "sub_fielder" not in STATUS_MAP
