from __future__ import annotations

from p11.analytics.players_percentiles import (
    AXES,
    mid_rank_percentile,
    percentile_of,
    population,
    sample_of,
)

AX = {a.key: a for a in AXES}


def _s(**kw: object):  # type: ignore[no-untyped-def]
    base: dict[str, object] = dict(
        bat_inns=20,
        bat_outs=15,
        runs=500,
        bat_balls=400,
        bowl_inns=0,
        bowl_balls=0,
        bowl_runs=0,
        wickets=0,
        matches=20,
        fielding=5,
        fantasy=[30] * 20,
    )
    base.update(kw)
    return sample_of(**base)  # type: ignore[arg-type]


def test_mid_rank_percentile_counts_ties_half() -> None:
    pop = [1.0, 2.0, 3.0, 4.0]
    assert mid_rank_percentile(pop, 1.0) == 12.5
    assert mid_rank_percentile(pop, 4.0) == 87.5
    assert mid_rank_percentile([2.0, 2.0], 2.0) == 50.0
    assert mid_rank_percentile(pop, 10.0) == 100.0
    assert mid_rank_percentile([], 1.0) is None


def test_sample_rates_and_eligibility() -> None:
    s = _s(bowl_inns=4, bowl_balls=96, bowl_runs=120, wickets=6)
    assert s.values["runs_per_inns"] == 25.0
    assert s.values["strike_rate"] == 125.0
    assert s.values["economy"] == 7.5
    assert s.eligible["strike_rate"]
    assert not s.eligible["economy"]  # 96 balls < 120
    nobat = _s(bat_inns=0, bat_outs=0, runs=0, bat_balls=0)
    assert nobat.values["average"] is None and not nobat.eligible["average"]


def test_percentiles_invert_lower_is_better_and_skip_small_samples() -> None:
    samples = {
        "tight": _s(bowl_inns=30, bowl_balls=600, bowl_runs=650, wickets=30),  # econ 6.5
        "mid": _s(bowl_inns=30, bowl_balls=600, bowl_runs=800, wickets=30),  # econ 8.0
        "leaky": _s(bowl_inns=30, bowl_balls=600, bowl_runs=1000, wickets=30),  # econ 10.0
        "tiny": _s(bowl_inns=1, bowl_balls=12, bowl_runs=5, wickets=1),  # ineligible
    }
    pop = population(samples)
    assert len(pop.sorted_by_axis["economy"]) == 3
    econ = AX["economy"]
    assert percentile_of(pop, econ, "tight") > percentile_of(pop, econ, "leaky")  # type: ignore[operator]
    assert percentile_of(pop, econ, "mid") == 50.0
    assert percentile_of(pop, econ, "tiny") is None
    assert percentile_of(pop, econ, "unknown") is None
    # every batting value ties -> everyone sits at the median
    assert percentile_of(pop, AX["strike_rate"], "tight") == 50.0
