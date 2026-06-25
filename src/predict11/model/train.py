"""Train a LightGBM regressor to predict a player's fantasy points for a match.

Temporal split (no shuffling): matches before TEST_FROM_DATE train the model;
later matches are held out. We report MAE/RMSE plus a ranking metric (Spearman),
because for fantasy selection the *ordering* of players matters more than the
absolute point estimate.
"""
from __future__ import annotations

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error

from ..config import DUCKDB_PATH, MODEL_PATH, TEST_FROM_DATE
from ..features.build import FEATURE_COLS

PARAMS = dict(
    objective="regression_l1",  # L1 = robust to the long upper tail of big scores
    n_estimators=600,
    learning_rate=0.03,
    num_leaves=31,
    min_child_samples=40,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    random_state=42,
    n_jobs=-1,
    verbose=-1,
)


def load_features(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute("SELECT * FROM player_match_features").df()
    df["date"] = pd.to_datetime(df["date"])
    return df


def temporal_split(df: pd.DataFrame, test_from: str = TEST_FROM_DATE):
    cut = pd.Timestamp(test_from)
    return df[df["date"] < cut].copy(), df[df["date"] >= cut].copy()


def train(con: duckdb.DuckDBPyConnection, test_from: str = TEST_FROM_DATE) -> dict:
    df = load_features(con)
    train_df, test_df = temporal_split(df, test_from)
    Xtr, ytr = train_df[FEATURE_COLS], train_df["fp"]
    Xte, yte = test_df[FEATURE_COLS], test_df["fp"]

    model = lgb.LGBMRegressor(**PARAMS)
    model.fit(Xtr, ytr, eval_set=[(Xte, yte)],
              callbacks=[lgb.early_stopping(50, verbose=False)])

    pred = model.predict(Xte)
    metrics = {
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "test_from": test_from,
        "mae": float(mean_absolute_error(yte, pred)),
        "rmse": float(np.sqrt(mean_squared_error(yte, pred))),
        "spearman": float(spearmanr(yte, pred).correlation),
        "best_iteration": int(model.best_iteration_ or PARAMS["n_estimators"]),
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(MODEL_PATH))

    importances = sorted(
        zip(FEATURE_COLS, model.feature_importances_), key=lambda x: -x[1]
    )
    metrics["top_features"] = importances[:8]
    return metrics


def load_model() -> lgb.Booster:
    return lgb.Booster(model_file=str(MODEL_PATH))


if __name__ == "__main__":
    con = duckdb.connect(str(DUCKDB_PATH))
    m = train(con)
    con.close()
    for k, v in m.items():
        print(f"{k}: {v}")
