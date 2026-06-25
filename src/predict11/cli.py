"""Command-line entrypoint that orchestrates the whole pipeline.

  predict11 ingest      YAML -> DuckDB
  predict11 build       compute Dream11 points (labels) + features
  predict11 train       train LightGBM, save model
  predict11 backtest    evaluate vs baselines
  predict11 all         ingest -> build -> train -> backtest
  predict11 predict A B  print the optimal XI for fixture team A vs team B
  predict11 serve       run the API + frontend (uvicorn)
"""
from __future__ import annotations

import argparse
import json

import duckdb

from .config import DUCKDB_PATH


def _con():
    return duckdb.connect(str(DUCKDB_PATH))


def cmd_ingest(_):
    from .data.ingest import ingest
    print(json.dumps(ingest(), indent=2))


def cmd_build(_):
    from .features.build import build_and_store
    from .scoring.fantasy_points import build_points_table
    con = _con()
    print("points rows:", build_points_table(con))
    print("feature rows:", build_and_store(con))
    con.close()


def cmd_train(_):
    from .model.train import train
    con = _con()
    for k, v in train(con).items():
        print(f"{k}: {v}")
    con.close()


def cmd_backtest(_):
    from .model.backtest import backtest
    con = _con()
    for k, v in backtest(con).items():
        print(f"{k}: {v}")
    con.close()


def cmd_all(args):
    cmd_ingest(args)
    cmd_build(args)
    cmd_train(args)
    cmd_backtest(args)


def cmd_predict(args):
    from .api.service import predict_fixture
    print(json.dumps(predict_fixture(args.team1, args.team2), indent=2))


def cmd_serve(args):
    import uvicorn
    uvicorn.run("predict11.api.app:app", host=args.host, port=args.port, reload=args.reload)


def main():
    p = argparse.ArgumentParser(prog="predict11")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest").set_defaults(func=cmd_ingest)
    sub.add_parser("build").set_defaults(func=cmd_build)
    sub.add_parser("train").set_defaults(func=cmd_train)
    sub.add_parser("backtest").set_defaults(func=cmd_backtest)
    sub.add_parser("all").set_defaults(func=cmd_all)

    pp = sub.add_parser("predict")
    pp.add_argument("team1")
    pp.add_argument("team2")
    pp.set_defaults(func=cmd_predict)

    ps = sub.add_parser("serve")
    ps.add_argument("--host", default="127.0.0.1")
    ps.add_argument("--port", type=int, default=8000)
    ps.add_argument("--reload", action="store_true")
    ps.set_defaults(func=cmd_serve)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
