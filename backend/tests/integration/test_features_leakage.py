"""Point-in-time guarantee of the model feature frame, against the real IPL data (read-only).

Perturb every outcome (fantasy points and ball-by-ball results) of a cut-off match and of all
later matches, rebuild, and require the cut-off match's features to be identical: a feature
that moves can only have read its own match or the future.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import Connection

from p11.features import build as fb

from .players_live import live  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration

OUTCOME_ROWS = ("batting", "bowling", "fielding", "total")
OUTCOME_BALLS = ("batter_runs", "total_runs", "byes", "legbyes", "wides", "noballs")


@pytest.fixture(scope="module")
def frames(live: Connection) -> tuple[pd.DataFrame, pd.DataFrame, int]:  # noqa: F811
    base = fb.build(live)
    # cut-off: a late-2026 league match (the first one on its date, so nothing else that day
    # precedes it in the chronological order)
    m26 = base[(base["year"] == 2026) & base["stage"].isna()]
    cut_seq = int(m26["seq"].quantile(0.8))
    cut_date = base.loc[base["seq"] == cut_seq, "date"].iloc[0]
    cut_seq = int(base.loc[base["date"] == cut_date, "seq"].min())
    late = set(base.loc[base["seq"] >= cut_seq, "match_id"])

    real_q = fb._q
    rng = np.random.default_rng(7)

    def perturbed(conn: Connection, sql: str) -> pd.DataFrame:
        df = real_q(conn, sql)
        hit = df["match_id"].isin(late) if "match_id" in df else None
        if sql is fb._SQL_ROWS:
            for c in OUTCOME_ROWS:
                df.loc[hit, c] = rng.integers(-10, 200, int(hit.sum()))
        elif sql is fb._SQL_BALLS:
            for c in OUTCOME_BALLS:
                df.loc[hit, c] = rng.integers(0, 7, int(hit.sum()))
            df.loc[hit, "wicket_kind"] = rng.choice(["caught", None, "bowled"], int(hit.sum()))
            df.loc[hit, "player_out_id"] = df.loc[hit, "batter_id"].where(
                df.loc[hit, "wicket_kind"].notna()
            )
            df.loc[hit, "fielder_ids"] = None
        return df

    fb._q = perturbed  # type: ignore[assignment]
    try:
        moved = fb.build(live)
    finally:
        fb._q = real_q  # type: ignore[assignment]
    return base, moved, cut_seq


def test_cutoff_match_features_unchanged_by_its_own_and_future_outcomes(
    frames: tuple[pd.DataFrame, pd.DataFrame, int],
) -> None:
    base, moved, cut_seq = frames
    key = ["match_id", "player_id"]
    a = base[base["seq"] == cut_seq].set_index(key).sort_index()
    b = moved[moved["seq"] == cut_seq].set_index(key).sort_index()
    assert len(a) >= 22 and a.index.equals(b.index)
    # sanity: the perturbation did change the outcomes
    assert not np.array_equal(a["total"].to_numpy(), b["total"].to_numpy())
    pd.testing.assert_frame_equal(a[fb.FEATURES], b[fb.FEATURES], check_exact=False, rtol=1e-9)


def test_frame_shape_and_coverage(frames: tuple[pd.DataFrame, pd.DataFrame, int]) -> None:
    base, _, _ = frames
    assert set(fb.FEATURES) <= set(base.columns)
    assert len(base) > 25_000 and base["seq"].is_monotonic_increasing
    assert not base.duplicated(["match_id", "player_id"]).any()
    # history-based features exist for nearly everyone with a previous IPL game
    experienced = base[base["n_prev"] >= 10]
    for f in ("mean_10", "ewm_5", "venue_par_20", "team_scored_10", "temp", "bats_first"):
        assert experienced[f].isna().mean() < 0.02, f
    # first appearances have no form (point in time), not zeros
    assert base.loc[base["n_prev"] == 0, "mean_5"].isna().all()
