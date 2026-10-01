"""Hindsight-best XI for hero B (role and team limits, C/VC multipliers)."""

from __future__ import annotations

from p11.analytics.home_xi import (
    TEAM_MAX,
    Candidate,
    best_xi,
    normalise_role,
    short_name,
)


def squad(team: str, pts: dict[str, list[float]]) -> list[Candidate]:
    return [
        Candidate(
            id=f"{team}-{role}-{i}", name=f"{team} {role} {i}", team=team, role=role, points=p
        )
        for role, ps in pts.items()
        for i, p in enumerate(ps)
    ]


def test_best_xi_respects_roles_and_picks_c_vc() -> None:
    cands = squad("GT", {"WK": [35], "BAT": [24, 22], "AR": [96, 84, 78, 20], "BOWL": [54, 44, 7]})
    cands += squad("RCB", {"WK": [39], "BAT": [151, 48, 45], "AR": [74, 46], "BOWL": [116, 79, 75]})
    pick = best_xi(cands)
    assert pick is not None
    roles = [c.role for c in pick.players]
    assert len(pick.players) == 11
    for r in ("WK", "BAT", "AR", "BOWL"):
        assert 1 <= roles.count(r) <= 8
    assert pick.captain.points == 151 and pick.vice.points == 116
    base = sum(c.points for c in pick.players)
    assert pick.total == round(base + 151 + 58, 1)
    # optimal: drop the weakest players, never a stronger one of the same role
    picked = {c.id for c in pick.players}
    assert "GT-BOWL-2" not in picked  # 7 pts


def test_best_xi_team_cap() -> None:
    strong = squad(
        "A", {"WK": [90, 80], "BAT": [90, 90, 90, 90], "AR": [90, 90, 90], "BOWL": [90, 90, 90]}
    )
    weak = squad("B", {"WK": [1], "BAT": [2], "AR": [3], "BOWL": [4]})
    pick = best_xi(strong + weak)
    assert pick is not None
    assert sum(c.team == "A" for c in pick.players) == TEAM_MAX


def test_best_xi_needs_every_role() -> None:
    assert best_xi(squad("A", {"BAT": [1] * 6, "BOWL": [1] * 6})) is None


def test_role_and_name_helpers() -> None:
    assert normalise_role("Wicket-Keeper") == "WK"
    assert normalise_role("all_rounder") == "AR"
    assert normalise_role("bowler") == "BOWL"
    assert normalise_role("BAT") == "BAT"
    assert normalise_role("coach") is None
    assert normalise_role(None) is None
    assert short_name("V Kohli") == "Kohli"
    assert short_name("B Sai Sudharsan") == "Sai Sudharsan"
    assert short_name("Rashid Khan") == "Rashid Khan"
