"""Vectorised point-in-time rolling helpers vs the straightforward per-group pandas version."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from p11.features.build import last_known, prev, roll_ewm, roll_max, roll_mean, roll_std, roll_sum


@pytest.fixture
def frame() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    n = 400
    df = pd.DataFrame(
        {
            "player_id": rng.choice(list("abcdefg"), n),
            "year": rng.choice([2024, 2025], n),
            "x": rng.integers(-5, 120, n).astype(float),
        }
    )
    df.loc[rng.choice(n, 60, replace=False), "x"] = np.nan  # gaps (e.g. did not bat)
    return df


def _ref(df: pd.DataFrame, key: str | list[str], fn) -> pd.Series:  # type: ignore[no-untyped-def]
    return df.groupby(key, sort=False)["x"].transform(lambda s: fn(s.shift(1)))


@pytest.mark.parametrize("k", [1, 3, 10, None])
def test_roll_mean_matches_pandas(frame: pd.DataFrame, k: int | None) -> None:
    exp = _ref(
        frame,
        "player_id",
        (lambda s: s.expanding().mean())
        if k is None
        else (lambda s: s.rolling(k, min_periods=1).mean()),
    )
    pd.testing.assert_series_equal(roll_mean(frame, "player_id", "x", k), exp, check_names=False)


def test_roll_mean_multi_key(frame: pd.DataFrame) -> None:
    exp = _ref(frame, ["player_id", "year"], lambda s: s.expanding().mean())
    got = roll_mean(frame, ["player_id", "year"], "x", None)
    pd.testing.assert_series_equal(got, exp, check_names=False)


@pytest.mark.parametrize("k", [5, None])
def test_roll_sum_treats_missing_as_zero(frame: pd.DataFrame, k: int | None) -> None:
    f = frame.assign(x=frame["x"].fillna(0))
    exp = _ref(
        f,
        "player_id",
        (lambda s: s.fillna(0).cumsum())
        if k is None
        else (lambda s: s.fillna(0).rolling(k, min_periods=1).sum()),
    ).fillna(0)
    got = roll_sum(frame, "player_id", "x", k)
    np.testing.assert_allclose(got.to_numpy(), exp.to_numpy(), atol=1e-9)


def test_std_max_ewm_last(frame: pd.DataFrame) -> None:
    np.testing.assert_allclose(
        roll_std(frame, "player_id", "x", 10).to_numpy(),
        _ref(frame, "player_id", lambda s: s.rolling(10, min_periods=3).std(ddof=0)).to_numpy(),
        atol=1e-6,
    )
    pd.testing.assert_series_equal(
        roll_max(frame, "player_id", "x", 10),
        _ref(frame, "player_id", lambda s: s.rolling(10, min_periods=1).max()),
        check_names=False,
    )
    np.testing.assert_allclose(
        roll_ewm(frame, "player_id", "x", 5).to_numpy(),
        _ref(frame, "player_id", lambda s: s.ewm(halflife=5).mean()).to_numpy(),
        atol=1e-9,
    )
    pd.testing.assert_series_equal(
        last_known(frame, "player_id", "x"),
        _ref(frame, "player_id", lambda s: s.ffill()),
        check_names=False,
    )


def test_point_in_time_never_sees_own_row() -> None:
    df = pd.DataFrame({"player_id": ["a", "a", "a"], "x": [10.0, 20.0, 30.0]})
    assert roll_mean(df, "player_id", "x", None).tolist()[1:] == [10.0, 15.0]
    assert np.isnan(roll_mean(df, "player_id", "x", None).iloc[0])
    assert prev(df, "player_id", "x").tolist()[1:] == [10.0, 20.0]
    assert roll_sum(df, "player_id", "x", None).tolist() == [0.0, 10.0, 30.0]
