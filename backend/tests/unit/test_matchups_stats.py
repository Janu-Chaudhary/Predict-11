"""Pair summary (D1) on synthetic balls (no DB)."""

from __future__ import annotations

import datetime as dt

from p11.analytics.matchups import _pair_stats
from p11.analytics.players_data import MatchInfo, Reference
from p11.analytics.players_stats import Ball


def _ref(n: int) -> Reference:
    matches = {
        i: MatchInfo(
            i, dt.date(2020 + i, 4, 1), 2020 + i, None, 1, 2, 1, "bat", "win", 1, None, None
        )
        for i in range(1, n + 1)
    }
    return Reference(matches, {i: i for i in matches}, {}, [], {}, {}, {})


def test_pair_stats_by_season_and_last_encounters() -> None:
    ref = _ref(7)
    balls = []
    for mid in range(1, 8):
        balls.append(Ball(mid, 1, 3, "bat", "bowl", batter_runs=mid % 3))
        balls.append(Ball(mid, 1, 3, "bat", "bowl", wides=1))
    balls.append(Ball(7, 1, 4, "bat", "bowl", wicket_kind="lbw", player_out="bat"))
    p = _pair_stats(ref, balls)
    assert p.balls == 8 and p.dismissals == 1 and p.how_out == {"lbw": 1}
    assert p.matches == 7 and p.confidence == "low"
    assert [s.season for s in p.by_season] == list(range(2021, 2028))
    assert len(p.last_encounters) == 5
    last = p.last_encounters[0]
    assert last.match_id == 7 and last.out and last.how_out == "lbw"
    assert last.summary == "2-1-1"  # balls-runs-dismissals
