"""Unit tests for p11.scoring: one hand-built micro-match per rule + band edges."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from fractions import Fraction

import pytest

from p11.scoring import (
    RULESETS,
    T20_2024,
    T20_2025,
    T20_2026,
    Delivery,
    HaulMode,
    LineupEntry,
    LineupStatus,
    MilestoneMode,
    Role,
    fantasy_team_points,
    get_ruleset,
    ruleset_for_date,
    score_match,
)
from p11.scoring.rules import band_points

R = T20_2025

# ------------------------------------------------------------------ helpers


def ball(batter="A", bowler="X", runs=0, *, over=0, innings=1, non_striker="B",
         extras=0, extra_type=None, wicket=None, out=None, fielders=(), **kw) -> Delivery:
    return Delivery(innings=innings, over=over, ball=0, batter=batter, bowler=bowler,
                    non_striker=non_striker, batter_runs=runs, extras=extras,
                    extra_type=extra_type, wicket_kind=wicket,
                    player_out=out if out or not wicket else batter,
                    fielders=tuple(fielders), **kw)


def balls(n, **kw) -> list[Delivery]:
    return [ball(**kw) for _ in range(n)]


def over_of(runs_seq, bowler="X", over=0, batter="A") -> list[Delivery]:
    return [ball(batter=batter, bowler=bowler, runs=r, over=over) for r in runs_seq]


DEFAULT_ROLES = {"A": Role.BAT, "B": Role.BAT, "X": Role.BOWL, "Y": Role.BOWL,
                 "F": Role.BAT, "G": Role.BAT, "H": Role.BAT, "K": Role.WK}


def score(deliveries, roles=None, statuses=None, rules=R):
    roles = {**DEFAULT_ROLES, **(roles or {})}
    statuses = statuses or {}
    lineup = [LineupEntry(p, "T1" if p in "ABK" else "T2", r,
                          statuses.get(p, LineupStatus.STARTING_XI))
              for p, r in roles.items()]
    return score_match(deliveries, lineup, rules)


def bat_with(runs: int, balls_n: int, role=Role.BAT, rules=R):
    """Batter A scores ``runs`` off ``balls_n`` balls, spread evenly (never a 4 or 6)."""
    per = [runs // balls_n + (1 if i < runs % balls_n else 0) for i in range(balls_n)]
    assert max(per, default=0) <= 3
    ds = [ball(runs=r) for r in per]
    return score(ds, roles={"A": role}, rules=rules)["A"]


def bowl_conceding(runs: int, legal: int, rules=R):
    """Bowler X bowls ``legal`` legal balls conceding ``runs`` (as singles)."""
    ds = []
    for i in range(legal):
        ds.append(ball(runs=1 if i < runs else 0, over=i // 6))
    assert runs <= legal
    return score(ds, rules=rules)["X"]


# ------------------------------------------------------------------ rule sets


class TestRuleSets:
    def test_registry_and_versions(self):
        assert set(RULESETS) == {"T20_2024", "T20_2025", "T20_2026"}
        assert get_ruleset("T20_2026") is T20_2026
        with pytest.raises(KeyError):
            get_ruleset("T20_1999")

    def test_frozen(self):
        with pytest.raises(AttributeError):
            T20_2025.wicket = 1  # type: ignore[misc]

    @pytest.mark.parametrize("d,version", [
        (date(2024, 4, 1), "T20_2024"),
        (date(2025, 3, 21), "T20_2024"),
        (date(2025, 3, 22), "T20_2025"),
        (date(2025, 12, 31), "T20_2025"),
        (date(2026, 1, 1), "T20_2026"),
        (date(2026, 5, 31), "T20_2026"),
    ])
    def test_ruleset_for_date(self, d, version):
        assert ruleset_for_date(d).version == version

    def test_before_earliest_raises(self):
        with pytest.raises(ValueError):
            ruleset_for_date(date(2019, 1, 1))

    def test_2026_values_equal_2025(self):
        a = {k: getattr(T20_2025, k) for k in T20_2025.__dataclass_fields__}
        b = {k: getattr(T20_2026, k) for k in T20_2026.__dataclass_fields__}
        for k in ("version", "effective_from", "notes"):
            a.pop(k), b.pop(k)
        assert a == b

    def test_current_point_values(self):
        r = T20_2026
        assert (r.run, r.boundary_bonus, r.six_bonus, r.duck) == (1, 4, 6, -2)
        assert r.run_milestones == ((25, 4), (50, 8), (75, 12), (100, 16))
        assert (r.dot_ball, r.wicket, r.lbw_bowled_bonus, r.maiden) == (1, 30, 8, 12)
        assert r.wicket_hauls == ((3, 4), (4, 8), (5, 12))
        assert (r.catch, r.catch_bonus, r.stumping) == (8, 4, 12)
        assert (r.runout_direct, r.runout_indirect) == (12, 6)
        assert (r.announced_lineup, r.substitute_played) == (4, 4)
        assert (r.captain_multiplier, r.vice_captain_multiplier) == (2.0, 1.5)
        assert (r.strike_rate_min_balls, r.economy_min_balls) == (10, 12)
        assert not r.count_super_over

    def test_legacy_values(self):
        r = T20_2024
        assert (r.boundary_bonus, r.six_bonus, r.wicket, r.dot_ball) == (1, 2, 25, 0)
        assert r.run_milestones == ((30, 4), (50, 8), (100, 16))
        assert r.wicket_hauls == ((3, 4), (4, 8), (5, 16))


# ------------------------------------------------------------------ bands (exact edges)


SR_CASES = [  # strike rate -> points
    ("170.01", 6), ("170", 4), ("150.01", 4), ("150", 2), ("130", 2), ("129.99", 0),
    ("100", 0), ("70.01", 0), ("70", -2), ("60", -2), ("59.99", -4), ("50", -4),
    ("49.99", -6), ("0", -6), ("400", 6),
]
ECON_CASES = [  # economy -> points
    ("0", 6), ("4.99", 6), ("5", 4), ("5.99", 4), ("5.995", 4), ("6", 2), ("7", 2),
    ("7.01", 0), ("9.99", 0), ("10", -2), ("11", -2), ("11.005", -4), ("11.01", -4),
    ("12", -4), ("12.01", -6), ("36", -6),
]


@pytest.mark.parametrize("sr,pts", SR_CASES)
def test_strike_rate_band_edges(sr, pts):
    assert band_points(R.strike_rate_bands, Fraction(sr)) == pts


@pytest.mark.parametrize("eco,pts", ECON_CASES)
def test_economy_band_edges(eco, pts):
    assert band_points(R.economy_bands, Fraction(eco)) == pts


# ------------------------------------------------------------------ batting


class TestBatting:
    def test_runs_fours_sixes(self):
        s = score([ball(runs=4), ball(runs=6), ball(runs=1), ball(runs=2)])["A"]
        assert (s.stats.runs, s.stats.fours, s.stats.sixes) == (13, 1, 1)
        assert s.items["runs"] == 13
        assert s.items["boundary_bonus"] == 4 and s.items["six_bonus"] == 6
        assert s.batting == 23

    def test_all_run_four_is_not_boundary(self):
        s = score([ball(runs=4, is_boundary=False)])["A"]
        assert s.stats.fours == 0 and s.batting == 4

    def test_extras_not_credited_to_batter(self):
        s = score([ball(extras=4, extra_type="byes"), ball(extras=1, extra_type="legbyes"),
                   ball(extras=5, extra_type="wides")])["A"]
        assert s.stats.runs == 0 and s.stats.fours == 0
        assert s.stats.balls_faced == 2  # wide is not a ball faced

    def test_noball_counts_as_ball_faced_and_batted_runs_count(self):
        s = score([ball(runs=6, extras=1, extra_type="noballs")])["A"]
        assert s.stats.balls_faced == 1 and s.stats.runs == 6 and s.stats.sixes == 1

    @pytest.mark.parametrize("runs,bonus", [
        (0, 0), (24, 0), (25, 4), (49, 4), (50, 8), (74, 8), (75, 12), (99, 12),
        (100, 16), (150, 16),
    ])
    def test_milestones_highest_only(self, runs, bonus):
        assert bat_with(runs, max(runs, 1)).items["run_milestone"] == bonus

    @pytest.mark.parametrize("runs,bonus", [
        (25, 4), (50, 12), (75, 24), (99, 24), (100, 16),
    ])
    def test_milestones_stack_below_century_mode(self, runs, bonus):
        rules = replace(R, milestone_mode=MilestoneMode.STACK_BELOW_CENTURY)
        assert bat_with(runs, runs, rules=rules).items["run_milestone"] == bonus

    @pytest.mark.parametrize("runs,bonus", [(29, 0), (30, 4), (50, 8), (100, 16)])
    def test_legacy_milestones(self, runs, bonus):
        assert bat_with(runs, runs, rules=T20_2024).items["run_milestone"] == bonus

    @pytest.mark.parametrize("role,pts", [
        (Role.BAT, -2), (Role.WK, -2), (Role.AR, -2), (Role.BOWL, 0),
    ])
    def test_duck_roles(self, role, pts):
        s = score([ball(), ball(wicket="bowled")], roles={"A": role})["A"]
        assert s.items["duck"] == pts

    def test_duck_on_diamond_runout_without_facing(self):
        # non-striker B run out for 0 without facing a ball
        s = score([ball(wicket="run out", out="B", fielders=["F"])])["B"]
        assert s.stats.balls_faced == 0 and s.items["duck"] == -2

    def test_no_duck_when_not_out_on_zero(self):
        assert score(balls(3))["A"].items["duck"] == 0

    def test_no_duck_with_runs(self):
        s = score([ball(runs=1), ball(wicket="caught", fielders=["F"])])["A"]
        assert s.items["duck"] == 0

    def test_legbyes_do_not_save_a_duck(self):
        s = score([ball(extras=1, extra_type="legbyes"), ball(wicket="bowled")])["A"]
        assert s.items["duck"] == -2  # leg-byes are not the batter's runs

    def test_retired_hurt_on_zero_is_not_a_duck(self):
        s = score([ball(), ball(wicket="retired hurt")])["A"]
        assert not s.stats.dismissed and s.items["duck"] == 0
        assert score([ball(wicket="retired hurt")])["X"].stats.wickets == 0

    def test_retired_out_on_zero_is_a_duck_but_no_bowler_wicket(self):
        sc = score([ball(), ball(wicket="retired out")])
        assert sc["A"].items["duck"] == -2 and sc["X"].stats.wickets == 0

    def test_strike_rate_min_balls(self):
        assert bat_with(9, 9).items["strike_rate"] == 0  # 9 balls: not eligible
        # 10 balls, 0 runs -> SR 0 -> -6
        assert bat_with(0, 10).items["strike_rate"] == -6

    @pytest.mark.parametrize("runs,balls_n,pts", [
        (17, 10, 4),   # 170.00 -> 150.01-170 band
        (18, 10, 6),   # 180
        (15, 10, 2),   # 150.00 -> 130-150 band
        (13, 10, 2),   # 130.00
        (12, 10, 0),   # 120
        (7, 10, -2),   # 70.00 -> -2 (negatives apply at 70 or below)
        (6, 10, -2),   # 60.00
        (11, 20, -4),  # 55
        (5, 10, -4),   # 50.00
        (49, 100, -6),  # 49.00
    ])
    def test_strike_rate_points(self, runs, balls_n, pts):
        assert bat_with(runs, balls_n).items["strike_rate"] == pts

    def test_strike_rate_exempt_for_bowler_both_ways(self):
        assert bat_with(0, 10, role=Role.BOWL).items["strike_rate"] == 0
        assert bat_with(10, 10, role=Role.BOWL).items["strike_rate"] == 0
        ds = [ball(runs=6)] * 10
        assert score(ds, roles={"A": Role.BOWL})["A"].items["strike_rate"] == 0
        assert score(ds, roles={"A": Role.AR})["A"].items["strike_rate"] == 6
        assert score(ds, roles={"A": Role.WK})["A"].items["strike_rate"] == 6

    def test_wides_do_not_count_towards_strike_rate_balls(self):
        ds = [ball(runs=0)] * 9 + [ball(extras=1, extra_type="wides")] * 3
        assert score(ds)["A"].items["strike_rate"] == 0


# ------------------------------------------------------------------ bowling


class TestBowling:
    @pytest.mark.parametrize("kind,wkt,bonus", [
        ("bowled", 30, 8), ("lbw", 30, 8), ("caught", 30, 0), ("stumped", 30, 0),
        ("hit wicket", 30, 0), ("caught and bowled", 30, 0),
        ("run out", 0, 0), ("obstructing the field", 0, 0), ("retired out", 0, 0),
        ("retired hurt", 0, 0), ("timed out", 0, 0), ("handled the ball", 0, 0),
    ])
    def test_wicket_kinds(self, kind, wkt, bonus):
        fielders = ["K"] if kind in ("caught", "stumped", "run out") else []
        s = score([ball(wicket=kind, fielders=fielders)])["X"]
        assert s.items["wickets"] == wkt
        assert s.items["lbw_bowled_bonus"] == bonus

    @pytest.mark.parametrize("n,bonus", [(1, 0), (2, 0), (3, 4), (4, 8), (5, 12), (6, 12)])
    def test_wicket_hauls_highest_only(self, n, bonus):
        names = ["A", "B", "F", "G", "H", "K"]
        ds = [ball(batter=names[i], wicket="caught", fielders=["Y"]) for i in range(n)]
        s = score(ds)["X"]
        assert s.stats.wickets == n and s.items["wicket_haul"] == bonus

    def test_wicket_haul_stack_mode(self):
        rules = replace(R, haul_mode=HaulMode.STACK)
        ds = [ball(batter=b, wicket="bowled") for b in ["A", "B", "F", "G", "H"]]
        assert score(ds, rules=rules)["X"].items["wicket_haul"] == 4 + 8 + 12

    def test_runouts_do_not_count_towards_haul(self):
        ds = [ball(batter=b, wicket="bowled") for b in ["A", "B"]]
        ds += [ball(batter="F", wicket="run out", fielders=["Y"])]
        assert score(ds)["X"].items["wicket_haul"] == 0

    def test_dot_balls(self):
        ds = [ball(), ball(runs=1), ball(wicket="bowled", batter="B"),
              ball(extras=1, extra_type="legbyes"), ball(extras=4, extra_type="byes"),
              ball(extras=1, extra_type="wides"), ball(extras=1, extra_type="noballs"),
              ball(extras=5, extra_type="penalty")]
        s = score(ds)["X"]
        # dot, wicket-dot, legbye-dot, bye-dot; wide/no-ball/runs/penalty are not
        assert s.stats.dot_balls == 4 and s.items["dot_balls"] == 4

    def test_runout_off_runs_is_not_a_dot(self):
        s = score([ball(runs=1, wicket="run out", out="B", fielders=["F"])])["X"]
        assert s.stats.dot_balls == 0

    def test_no_dot_points_in_legacy(self):
        assert score(balls(6), rules=T20_2024)["X"].items["dot_balls"] == 0

    def test_maiden(self):
        s = score(over_of([0] * 6))["X"]
        assert s.stats.maidens == 1 and s.items["maidens"] == 12

    def test_maiden_with_byes_and_legbyes(self):
        ds = over_of([0] * 4) + [ball(extras=4, extra_type="byes"),
                                 ball(extras=1, extra_type="legbyes")]
        assert score(ds)["X"].stats.maidens == 1

    def test_wide_or_noball_spoils_maiden(self):
        for et in ("wides", "noballs"):
            ds = over_of([0] * 6) + [ball(extras=1, extra_type=et)]
            assert score(ds)["X"].stats.maidens == 0

    def test_partial_over_is_not_maiden(self):
        assert score(over_of([0] * 5))["X"].stats.maidens == 0

    def test_run_conceded_spoils_maiden(self):
        assert score(over_of([0, 0, 0, 0, 0, 1]))["X"].stats.maidens == 0

    def test_shared_over_is_not_maiden(self):
        ds = over_of([0] * 3, bowler="X") + over_of([0] * 3, bowler="Y")
        sc = score(ds)
        assert sc["X"].stats.maidens == 0 and sc["Y"].stats.maidens == 0

    def test_maiden_per_innings_over(self):
        ds = over_of([0] * 6) + [ball(over=0, innings=2, bowler="X") for _ in range(6)]
        assert score(ds)["X"].stats.maidens == 2

    def test_wicket_maiden(self):
        ds = over_of([0] * 5) + [ball(wicket="lbw")]
        s = score(ds)["X"]
        assert s.bowling == 6 + 30 + 8 + 12  # dots + wicket + lbw + maiden

    def test_economy_min_two_overs(self):
        assert bowl_conceding(0, 11).items["economy"] == 0
        assert bowl_conceding(0, 12).items["economy"] == 6

    @pytest.mark.parametrize("runs,legal,pts", [
        (9, 12, 6),    # 4.50
        (10, 12, 4),   # 5.00
        (11, 12, 4),   # 5.50
        (12, 12, 2),   # 6.00
        (14, 12, 2),   # 7.00
        (15, 12, 0),   # 7.50
        (20, 12, -2),  # 10.00
        (30, 18, -2),  # 10.00 over 3 overs
        (44, 18, -6),  # 14.67
    ])
    def test_economy_points(self, runs, legal, pts):
        ds = [ball(runs=runs // legal + (1 if i < runs % legal else 0), over=i // 6)
              for i in range(legal)]
        assert score(ds)["X"].items["economy"] == pts

    @pytest.mark.parametrize("conceded,pts", [(22, -2), (23, -4), (24, -4), (25, -6)])
    def test_economy_upper_bands_two_overs(self, conceded, pts):
        # 2 overs: 22 -> 11.0, 23 -> 11.5, 24 -> 12.0, 25 -> 12.5
        ds = [ball(runs=2, over=i // 6) for i in range(11)] + [ball(runs=conceded - 22, over=1)]
        assert score(ds)["X"].items["economy"] == pts

    def test_byes_legbyes_not_charged_wides_noballs_are(self):
        ds = [ball(extras=4, extra_type="byes", over=i // 6) for i in range(12)]
        s = score(ds)["X"]
        assert s.stats.runs_conceded == 0 and s.items["economy"] == 6
        ds = [ball(over=i // 6) for i in range(12)] + [ball(extras=5, extra_type="wides")] * 3
        s = score(ds)["X"]
        assert s.stats.runs_conceded == 15 and s.stats.legal_balls_bowled == 12
        assert s.items["economy"] == 0  # 15 runs / 2 overs = 7.50 -> no band

    def test_noball_with_byes_detail(self):
        d = ball(runs=0, extras=5, extra_type="noballs",
                 extras_detail={"noballs": 1, "byes": 4})
        s = score([d])["X"]
        assert s.stats.runs_conceded == 1 and s.stats.legal_balls_bowled == 0

    def test_economy_three_overs_mixed(self):
        # 18 legal balls, 30 runs -> 10.00 -> -2
        ds = [ball(runs=2 if i < 12 else 1, over=i // 6) for i in range(18)]
        assert score(ds)["X"].items["economy"] == -2


# ------------------------------------------------------------------ fielding


class TestFielding:
    def test_catch(self):
        s = score([ball(wicket="caught", fielders=["F"])])["F"]
        assert s.items["catches"] == 8 and s.fielding == 8

    @pytest.mark.parametrize("n,bonus", [(2, 0), (3, 4), (4, 4), (6, 4)])
    def test_three_catch_bonus_once(self, n, bonus):
        bats = ["A", "B", "G", "H", "K", "Y"]
        ds = [ball(batter=bats[i], wicket="caught", fielders=["F"]) for i in range(n)]
        s = score(ds)["F"]
        assert s.items["catches"] == 8 * n and s.items["catch_bonus"] == bonus

    def test_caught_and_bowled_gives_bowler_catch(self):
        s = score([ball(wicket="caught and bowled")])["X"]
        assert s.items["wickets"] == 30 and s.items["catches"] == 8

    def test_stumping(self):
        sc = score([ball(wicket="stumped", fielders=["K"])])
        assert sc["K"].items["stumpings"] == 12 and sc["X"].items["wickets"] == 30

    def test_runout_direct_inferred_single_fielder(self):
        s = score([ball(wicket="run out", fielders=["F"])])["F"]
        assert s.items["runout_direct"] == 12 and s.items["runout_indirect"] == 0

    def test_runout_indirect_two_fielders(self):
        sc = score([ball(wicket="run out", fielders=["F", "K"])])
        assert sc["F"].items["runout_indirect"] == 6 and sc["K"].items["runout_indirect"] == 6
        assert sc["F"].items["runout_direct"] == 0

    def test_runout_three_fielders_last_two_only(self):
        sc = score([ball(wicket="run out", fielders=["G", "F", "K"])])
        assert sc["G"].fielding == 0
        assert sc["F"].fielding == 6 and sc["K"].fielding == 6

    def test_runout_explicit_flags(self):
        sc = score([ball(wicket="run out", fielders=["F"], runout_direct=False)])
        assert sc["F"].items["runout_indirect"] == 6
        sc = score([ball(wicket="run out", fielders=["F", "K"], runout_direct=True)])
        assert sc["F"].items["runout_direct"] == 12 and sc["K"].fielding == 0

    def test_runout_not_a_bowler_wicket(self):
        assert score([ball(wicket="run out", fielders=["F"])])["X"].items["wickets"] == 0

    def test_runout_without_fielders_scores_nobody(self):
        sc = score([ball(wicket="run out")])
        assert all(p.fielding == 0 for p in sc.players.values())

    def test_substitute_fielder_not_in_lineup_scores_nothing(self):
        sc = score([ball(wicket="caught", fielders=["SUB"])])
        assert "SUB" not in sc.players and "SUB" in sc.unscored_participants
        assert sc["X"].items["wickets"] == 30


# ------------------------------------------------------------------ lineup / impact


class TestLineup:
    def test_starting_xi_gets_four_without_playing_a_ball(self):
        s = score([ball()])["H"]
        assert s.lineup == 4 and s.total == 4

    def test_impact_player_in_gets_four_plus_contributions(self):
        sc = score([ball(batter="G", runs=4)],
                   statuses={"G": LineupStatus.SUBSTITUTE_PLAYED})
        assert sc["G"].lineup == 4 and sc["G"].total == 4 + 4 + 4

    def test_impact_player_out_keeps_points(self):
        # X bowled before being subbed out: still STARTING_XI, keeps everything
        sc = score([ball(wicket="bowled")], statuses={"Y": LineupStatus.SUBSTITUTE_PLAYED})
        assert sc["X"].lineup == 4 and sc["X"].items["wickets"] == 30

    def test_unused_substitute_zero(self):
        sc = score([ball()], statuses={"H": LineupStatus.SUBSTITUTE_UNUSED})
        assert sc["H"].total == 0

    def test_unused_substitute_seen_in_data_is_promoted(self):
        sc = score([ball(wicket="caught", fielders=["H"])],
                   statuses={"H": LineupStatus.SUBSTITUTE_UNUSED})
        assert sc["H"].status is LineupStatus.SUBSTITUTE_PLAYED
        assert sc["H"].total == 4 + 8 and sc.warnings

    def test_withdrawn_player_scores_nothing(self):
        sc = score([ball(runs=6)], statuses={"A": LineupStatus.WITHDRAWN})
        assert sc["A"].total == 0

    def test_duplicate_lineup_rejected(self):
        e = LineupEntry("A", "T1", Role.BAT)
        with pytest.raises(ValueError):
            score_match([], [e, e], R)


# ------------------------------------------------------------------ scope / totals


class TestMatchLevel:
    def test_super_over_ignored(self):
        so = [ball(runs=6, super_over=True, innings=3), ball(wicket="bowled", super_over=True,
                                                            innings=3)]
        sc = score(so)
        assert sc["A"].total == 4 and sc["X"].total == 4

    def test_super_over_counted_when_rule_says_so(self):
        rules = replace(R, count_super_over=True)
        assert score([ball(runs=6, super_over=True)], rules=rules)["A"].stats.runs == 6

    def test_components_sum(self):
        ds = (over_of([4, 6, 1, 0, 0, 1]) + over_of([0] * 6, over=1)
              + [ball(wicket="caught", fielders=["F"], over=2)])
        for p in score(ds).players.values():
            assert p.batting + p.bowling + p.fielding + p.lineup + p.bonuses == p.total
            assert sum(p.items.values()) == p.total

    def test_full_hand_computed_bowler(self):
        # X: over 0 maiden incl. bowled wicket; over 1 concedes 6 (no wkts) -> 2-1-6-1
        ds = over_of([0, 0, 0, 0, 0]) + [ball(wicket="bowled")]
        ds += over_of([1, 1, 1, 1, 1, 1], over=1, batter="B")
        x = score(ds)["X"]
        # dots 6, wicket 30, bowled 8, maiden 12 ; economy 3.0 -> +6 ; lineup 4
        assert x.bowling == 6 + 30 + 8 + 12
        assert x.bonuses == 6
        assert x.total == 56 + 6 + 4

    def test_same_scorer_across_versions(self):
        ds = [ball(runs=4), ball(runs=6), ball(wicket="bowled")]
        new = score(ds, rules=T20_2026)
        old = score(ds, rules=T20_2024)
        assert new["A"].batting == 10 + 4 + 6 and old["A"].batting == 10 + 1 + 2
        assert new["X"].bowling == 1 + 30 + 8 and old["X"].bowling == 0 + 25 + 8


class TestMultipliers:
    def test_captain_and_vice_captain(self):
        sc = score([ball(runs=6), ball(runs=4, batter="B")])
        a, b = sc["A"].total, sc["B"].total
        picks = ["A", "B", "X"]
        got = fantasy_team_points(sc, picks, "A", "B", R)
        assert got == pytest.approx(2 * a + 1.5 * b + sc["X"].total)

    def test_vice_captain_half_points(self):
        sc = score([ball(runs=1)])  # A: 1 + 4 = 5 -> VC 7.5
        assert fantasy_team_points(sc, ["B", "A"], "B", "A", R) == pytest.approx(8 + 7.5)

    def test_invalid_captaincy(self):
        sc = score([])
        with pytest.raises(ValueError):
            fantasy_team_points(sc, ["A", "B"], "A", "A", R)
        with pytest.raises(ValueError):
            fantasy_team_points(sc, ["A", "B"], "A", "X", R)
