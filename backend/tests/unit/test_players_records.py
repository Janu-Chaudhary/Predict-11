from __future__ import annotations

from p11.analytics.players_records import MILESTONE_RULES, milestone_for

RULES = {r.stat: r for r in MILESTONE_RULES}


def test_runs_milestones_use_500s_below_1000_and_1000s_above() -> None:
    assert milestone_for(RULES["runs"], 980) == (1000, 20)
    assert milestone_for(RULES["runs"], 450) == (500, 50)
    assert milestone_for(RULES["runs"], 2955) == (3000, 45)
    assert milestone_for(RULES["runs"], 1982) == (2000, 18)
    assert milestone_for(RULES["runs"], 1500) is None  # 500 short of 2000: out of reach


def test_wickets_sixes_matches_catches() -> None:
    assert milestone_for(RULES["wickets"], 148) == (150, 2)
    assert milestone_for(RULES["wickets"], 96) == (100, 4)
    assert milestone_for(RULES["wickets"], 130) is None
    assert milestone_for(RULES["sixes"], 289) == (300, 11)
    assert milestone_for(RULES["matches"], 95) == (100, 5)
    assert milestone_for(RULES["catches"], 49) == (50, 1)
    assert milestone_for(RULES["catches"], 0) is None
