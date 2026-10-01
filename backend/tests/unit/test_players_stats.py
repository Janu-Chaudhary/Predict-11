"""Stat definitions on synthetic deliveries (no DB)."""

from __future__ import annotations

import pytest

from p11.analytics.players_stats import (
    Ball,
    BattingCard,
    BowlingCard,
    batting_cards,
    batting_line,
    batting_phases,
    bowling_cards,
    bowling_line,
    bowling_phases,
    confidence,
    fielding,
    h2h,
    next_milestone,
    overs_str,
    phase_of,
    streak,
)

BAT, NS, BOWL, FLD = "bat", "ns", "bowl", "fld"


def ball(**kw: object) -> Ball:
    base: dict[str, object] = {
        "match_id": 1,
        "innings": 1,
        "over": 0,
        "batter": BAT,
        "bowler": BOWL,
        "non_striker": NS,
    }
    base.update(kw)
    return Ball(**base)  # type: ignore[arg-type]


def test_phase_boundaries_are_zero_indexed_overs() -> None:
    assert [phase_of(o) for o in (0, 5, 6, 14, 15, 19)] == [
        "powerplay",
        "powerplay",
        "middle",
        "middle",
        "death",
        "death",
    ]


def test_wides_are_not_balls_faced_but_no_balls_are() -> None:
    balls = [
        ball(batter_runs=1),
        ball(wides=1),  # not faced, 0 runs to batter
        ball(wides=5),  # wide that went for four: still not faced
        ball(noballs=1, batter_runs=4),  # faced; runs count for the batter
        ball(batter_runs=0),
    ]
    (c,) = batting_cards(balls, BAT)
    assert (c.runs, c.balls, c.fours) == (5, 3, 1)
    assert c.dots == 1  # only the legal dot; a no-ball is never a dot
    assert batting_line([c]).strike_rate == pytest.approx(166.67)


def test_bowler_charged_wides_and_no_balls_not_byes_or_legbyes() -> None:
    balls = [
        ball(batter_runs=2),
        ball(wides=1),
        ball(wides=5),
        ball(noballs=1, batter_runs=1),
        ball(byes=4),
        ball(legbyes=1),
        ball(batter_runs=0),
        ball(batter_runs=0),
    ]
    (c,) = bowling_cards(balls, BOWL)
    assert c.runs == 2 + 1 + 5 + 1 + 1  # byes/leg-byes not charged
    assert c.balls == 5  # legal balls only: excludes wides and the no-ball
    assert c.dots == 4  # legal balls with 0 charged: byes, leg-byes, two dots
    assert c.wides == 2 and c.noballs == 1
    ln = bowling_line([c])
    assert ln.economy == pytest.approx(10 / 5 * 6)
    assert ln.overs == "0.5"


def test_retired_hurt_is_not_a_dismissal_and_average_handles_no_outs() -> None:
    balls = [ball(batter_runs=10), ball(wicket_kind="retired hurt", player_out=BAT)]
    (c,) = batting_cards(balls, BAT)
    assert not c.out
    ln = batting_line([c])
    assert ln.not_outs == 1 and ln.average is None
    (w,) = bowling_cards(balls, BOWL)
    assert w.wickets == 0


def test_retired_out_is_a_batting_dismissal_but_not_a_bowler_wicket() -> None:
    balls = [ball(batter_runs=3, wicket_kind="retired out", player_out=BAT)]
    (c,) = batting_cards(balls, BAT)
    assert c.out and c.how_out == "retired out"
    assert bowling_cards(balls, BOWL)[0].wickets == 0


def test_non_striker_run_out_counts_for_non_striker_innings_not_bowler() -> None:
    balls = [
        ball(batter_runs=1),
        ball(batter_runs=0, wicket_kind="run out", player_out=NS, fielders=(FLD,)),
    ]
    ns_cards = batting_cards(balls, NS)
    assert len(ns_cards) == 1  # an innings even without facing a ball
    assert ns_cards[0].out and ns_cards[0].balls == 0 and ns_cards[0].duck
    assert not batting_cards(balls, BAT)[0].out
    assert bowling_cards(balls, BOWL)[0].wickets == 0
    assert fielding(balls, FLD).run_outs == 1
    # batting phase "outs" attribute the non-striker's dismissal to that ball's phase
    assert batting_phases(balls, NS)["powerplay"].outs == 1


@pytest.mark.parametrize(
    ("kind", "fielders", "bowler_wkt", "catch", "stump"),
    [
        ("caught", (FLD,), True, 1, 0),
        ("caught and bowled", (), True, 0, 0),
        ("stumped", (FLD,), True, 0, 1),
        ("bowled", (), True, 0, 0),
        ("lbw", (), True, 0, 0),
        ("hit wicket", (), True, 0, 0),
        ("obstructing the field", (), False, 0, 0),
        ("run out", (FLD,), False, 0, 0),
    ],
)
def test_bowler_wicket_kinds_and_fielding(
    kind: str, fielders: tuple[str, ...], bowler_wkt: bool, catch: int, stump: int
) -> None:
    balls = [ball(wicket_kind=kind, player_out=BAT, fielders=fielders)]
    assert bowling_cards(balls, BOWL)[0].wickets == int(bowler_wkt)
    assert batting_cards(balls, BAT)[0].out  # all of these dismiss the batter
    f = fielding(balls, FLD)
    assert (f.catches, f.stumpings) == (catch, stump)


def test_caught_and_bowled_is_the_bowlers_catch() -> None:
    balls = [ball(wicket_kind="caught and bowled", player_out=BAT)]
    assert fielding(balls, BOWL).catches == 1


def test_non_boundary_four_is_not_a_four() -> None:
    (c,) = batting_cards([ball(batter_runs=4, non_boundary=True), ball(batter_runs=6)], BAT)
    assert (c.runs, c.fours, c.sixes) == (10, 0, 1)


def test_maiden_needs_six_legal_balls_and_nothing_charged() -> None:
    maiden = [ball(over=3, legbyes=1)] + [ball(over=3) for _ in range(5)]
    not_maiden = [ball(over=4, wides=1)] + [ball(over=4) for _ in range(6)]
    (c,) = bowling_cards(maiden + not_maiden, BOWL)
    assert c.maidens == 1 and c.balls == 12 and c.runs == 1


def test_lines_and_best_figures() -> None:
    bats = [
        BattingCard(1, 1, runs=50, balls=30, out=True),
        BattingCard(2, 1, runs=113, balls=60, out=False),
        BattingCard(3, 1, runs=113, balls=70, out=True),
        BattingCard(4, 1, runs=0, balls=1, out=True),
        BattingCard(5, 1, runs=0, balls=0, out=False),
    ]
    ln = batting_line(bats)
    assert (ln.innings, ln.not_outs, ln.runs) == (5, 2, 276)
    assert ln.average == pytest.approx(92.0)
    assert (ln.fifties, ln.hundreds, ln.ducks, ln.thirties) == (1, 2, 1, 3)
    assert ln.highest_str == "113*"  # not-out ranks above an equal dismissed score

    bowls = [
        BowlingCard(1, 1, balls=24, runs=30, wickets=3),
        BowlingCard(2, 1, balls=24, runs=17, wickets=4),
        BowlingCard(3, 1, balls=24, runs=12, wickets=4),
        BowlingCard(4, 1, balls=12, runs=20, wickets=0),
    ]
    bl = bowling_line(bowls)
    assert bl.best == "4/12"
    assert (bl.three_plus, bl.four_plus, bl.five_plus) == (3, 2, 0)
    assert bl.average == pytest.approx(79 / 11, abs=0.01)
    assert bl.strike_rate == pytest.approx(84 / 11, abs=0.01)
    assert bl.economy == pytest.approx(79 / 84 * 6, abs=0.01)
    assert bl.overs == "14"
    assert overs_str(25) == "4.1"


def test_bowling_phases_and_economy() -> None:
    balls = [ball(over=0, batter_runs=4), ball(over=0, wides=1), ball(over=10)]
    balls += [ball(over=17, batter_runs=6, bowler="other")]
    ph = bowling_phases(balls, BOWL)
    assert ph["powerplay"].balls == 1 and ph["powerplay"].runs == 5
    assert ph["powerplay"].economy == pytest.approx(30.0)
    assert ph["middle"].dots == 1
    assert ph["death"].balls == 0 and ph["death"].economy is None


def test_h2h_counts_only_bowler_credited_dismissals_of_the_striker() -> None:
    balls = [
        ball(batter_runs=4),
        ball(wides=1),
        ball(noballs=1, batter_runs=0),
        ball(batter_runs=0, wicket_kind="run out", player_out=BAT, fielders=(FLD,)),
        ball(match_id=2, batter_runs=6),
        ball(match_id=2, wicket_kind="caught", player_out=BAT, fielders=(FLD,)),
    ]
    agg = h2h(balls)
    assert agg.balls == 5  # wide excluded
    assert agg.runs == 10
    assert agg.dismissals == 1 and agg.how_out == {"caught": 1}
    assert agg.dots == 2  # run-out ball and the catch; not the no-ball
    assert (agg.fours, agg.sixes) == (1, 1)
    assert len(agg.matches) == 2
    assert agg.strike_rate == pytest.approx(200.0)
    assert agg.boundary_pct == pytest.approx(40.0)


def test_confidence_badge_thresholds() -> None:
    assert [confidence(b) for b in (0, 11, 12, 29, 30, 108)] == [
        "low",
        "low",
        "medium",
        "medium",
        "high",
        "high",
    ]


def test_streak_current_and_longest() -> None:
    s = streak([1, 1, 0, 1, 1, 1, 0, 1, 1], lambda x: x == 1)
    assert (s.current, s.longest, s.longest_start, s.longest_end) == (2, 3, 3, 5)
    s = streak([0, 0], lambda x: x == 1)
    assert (s.current, s.longest, s.longest_start) == (0, 0, None)


def test_next_milestone() -> None:
    assert next_milestone(2955, 1000) == 3000
    assert next_milestone(3000, 1000) == 4000
    assert next_milestone(148, 50) == 150
