"""`p11` command-line entrypoint. Subcommands are added as phases land."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _out(obj: Any) -> None:
    json.dump(obj, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def _cricsheet_dir() -> Path:
    from p11.core.settings import get_settings

    return get_settings().data_dir / "raw" / "cricsheet"


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("p11.api.app:app", host=args.host, port=args.port, reload=args.reload)


def cmd_cricsheet_download(args: argparse.Namespace) -> None:
    from p11.ingest.sources import cricsheet

    d = _cricsheet_dir()
    got = []
    for name in args.zip:
        got.append(str(cricsheet.download_zip(name, d)))
    if args.register:
        got += [str(p) for p in cricsheet.download_register(d)]
    _out({"downloaded": got})


def cmd_registry_load(args: argparse.Namespace) -> None:
    from p11.core.db import engine
    from p11.registry.people import load_registry

    d = _cricsheet_dir()
    people = Path(args.people) if args.people else d / "people.csv"
    names = Path(args.names) if args.names else d / "names.csv"
    with engine().begin() as conn:
        log = load_registry(conn, people, names)
    _out({"changes": log.as_dict(), "row_changes": log.total})


def cmd_backfill_cricsheet(args: argparse.Namespace) -> None:
    from p11.core.db import engine
    from p11.core.settings import get_settings
    from p11.ingest.backfill import backfill_zip

    z = Path(args.zip)
    if not z.suffix:
        z = _cricsheet_dir() / f"{args.zip}.zip"
    rep = backfill_zip(engine(), z, get_settings().raw_archive_dir, force=args.force)
    out = rep.summary()
    out["quarantined_matches"] = rep.quarantined
    out["error_files"] = rep.errors
    _out(out)


def cmd_credits_load(args: argparse.Namespace) -> None:
    from p11.core.db import engine
    from p11.core.settings import get_settings
    from p11.registry.credits import load_credits

    teams = Path(args.dir) if args.dir else get_settings().data_dir / "raw" / "Teams"
    with engine().begin() as conn:
        rep = load_credits(conn, teams, args.season)
    _out(
        {
            "season": rep.season,
            "rows": rep.rows,
            "matched": rep.matched,
            "unmatched": [f"{r.team}: {r.name} / {r.full_name!r}" for r in rep.unmatched],
            "ambiguous": [f"{r.team}: {r.full_name!r} -> {ids}" for r, ids in rep.ambiguous],
            "matched_by_initial_surname": [f"{r.team}: {r.name} -> {pid}" for r, pid in rep.fuzzy],
            "no_credits_in_csv": [f"{r.team}: {r.name}" for r in rep.no_credits],
            "duplicates": [f"{r.team}: {r.full_name!r} -> {pid}" for r, pid in rep.duplicates],
            "changes": vars(rep.changes),
        }
    )


def cmd_credits_show(args: argparse.Namespace) -> None:
    from p11.core.db import engine
    from p11.registry.credits import credits_for_season

    with engine().connect() as conn:
        eff, credits = credits_for_season(conn, args.season)
    _out({"season": args.season, "effective_season": eff, "players": len(credits)})


def cmd_dq_report(args: argparse.Namespace) -> None:
    from p11.core.db import engine
    from p11.ingest.dq import dq_report

    with engine().connect() as conn:
        rep = dq_report(conn)
    if not args.full:
        rep["by_season"] = len(rep["by_season"])
    _out(rep)


def cmd_lake_export(args: argparse.Namespace) -> None:
    from p11.core.db import engine
    from p11.core.settings import get_settings
    from p11.ingest.lake import export_lake

    d = Path(args.dir) if args.dir else get_settings().lake_dir
    _out({"lake_dir": str(d), "rows": export_lake(engine(), d)})


def cmd_attributes_load(args: argparse.Namespace) -> None:
    from p11.core.db import engine
    from p11.ingest.player_attributes import coverage, load_all

    with engine().begin() as conn:
        out = load_all(conn, fetch_espn=args.fetch_espn)
        out["coverage"] = coverage(conn)
    _out(out)


def cmd_attributes_coverage(args: argparse.Namespace) -> None:
    from p11.core.db import engine
    from p11.ingest.player_attributes import coverage, derived_accuracy

    with engine().connect() as conn:
        _out({"coverage": coverage(conn), "derived_accuracy": derived_accuracy(conn)})


def cmd_starttime_load(args: argparse.Namespace) -> None:
    from p11.core.db import engine
    from p11.ingest.start_times import load_start_times

    with engine().begin() as conn:
        _out(load_start_times(conn, infer=not args.no_infer))


def cmd_fantasy_compute(args: argparse.Namespace) -> None:
    from p11.core.db import engine
    from p11.fantasy.compute import compute_points

    with engine().begin() as conn:
        _out(compute_points(conn, args.season, force=args.force).as_dict())


def cmd_fantasy_validate(args: argparse.Namespace) -> None:
    from p11.core.db import engine
    from p11.fantasy.validate import validate_2026

    with engine().connect() as conn:
        rep = validate_2026(conn)
    if not args.full:
        rep.pop("results")
    _out(rep)
    if rep["failed"]:
        sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="p11")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("serve", help="run the API")
    ps.add_argument("--host", default="127.0.0.1")
    ps.add_argument("--port", type=int, default=8000)
    ps.add_argument("--reload", action="store_true")
    ps.set_defaults(func=cmd_serve)

    pc = sub.add_parser("cricsheet", help="Cricsheet downloads").add_subparsers(
        dest="sub", required=True
    )
    x = pc.add_parser(
        "download", help="download <name>.zip (+ register CSVs) to data/raw/cricsheet"
    )
    x.add_argument(
        "--zip", nargs="*", default=["ipl_json"], help="e.g. ipl_json recently_added_2_json"
    )
    x.add_argument("--register", action="store_true", help="also people.csv + names.csv")
    x.set_defaults(func=cmd_cricsheet_download)

    pr = sub.add_parser("registry", help="player registry").add_subparsers(
        dest="sub", required=True
    )
    x = pr.add_parser("load", help="people.csv/names.csv -> player, player_source_id, alias")
    x.add_argument("--people")
    x.add_argument("--names")
    x.set_defaults(func=cmd_registry_load)

    pb = sub.add_parser("backfill", help="historical loads").add_subparsers(
        dest="sub", required=True
    )
    x = pb.add_parser("cricsheet", help="load a Cricsheet JSON zip")
    x.add_argument("--zip", default="ipl_json", help="zip name in data/raw/cricsheet or a path")
    x.add_argument("--force", action="store_true", help="re-parse unchanged payloads too")
    x.set_defaults(func=cmd_backfill_cricsheet)

    pcr = sub.add_parser("credits", help="Dream11 credits").add_subparsers(
        dest="sub", required=True
    )
    x = pcr.add_parser("load", help="data/raw/Teams/*.csv -> season_credits")
    x.add_argument("--season", type=int, required=True)
    x.add_argument("--dir")
    x.set_defaults(func=cmd_credits_load)
    x = pcr.add_parser("show", help="effective credits season (with fallback)")
    x.add_argument("--season", type=int, required=True)
    x.set_defaults(func=cmd_credits_show)

    pd = sub.add_parser("dq", help="data quality").add_subparsers(dest="sub", required=True)
    x = pd.add_parser("report")
    x.add_argument("--full", action="store_true", help="include per-season counts")
    x.set_defaults(func=cmd_dq_report)

    pl = sub.add_parser("lake", help="parquet lake").add_subparsers(dest="sub", required=True)
    x = pl.add_parser("export", help="write deliveries/matches/match_players parquet")
    x.add_argument("--dir")
    x.set_defaults(func=cmd_lake_export)

    pa = sub.add_parser("attributes", help="player role / hand / bowling style").add_subparsers(
        dest="sub", required=True
    )
    x = pa.add_parser("load", help="all sources -> player_attribute (+ player_media)")
    x.add_argument(
        "--fetch-espn",
        action="store_true",
        help="fetch missing ESPN athlete profiles (<= 1 req/s, cached in data/archive)",
    )
    x.set_defaults(func=cmd_attributes_load)
    x = pa.add_parser("coverage", help="attribute + photo coverage report")
    x.set_defaults(func=cmd_attributes_coverage)

    pst = sub.add_parser("starttime", help="match start times").add_subparsers(
        dest="sub", required=True
    )
    x = pst.add_parser("load", help="cached BCCI/ESPN times + validated day/night inference")
    x.add_argument("--no-infer", action="store_true")
    x.set_defaults(func=cmd_starttime_load)

    pf = sub.add_parser("fantasy", help="persisted Dream11 points").add_subparsers(
        dest="sub", required=True
    )
    x = pf.add_parser("compute", help="score matches -> player_match_points (idempotent)")
    x.add_argument("--season", type=int, nargs="*", help="e.g. --season 2025 2026 (default all)")
    x.add_argument("--force", action="store_true", help="rescore matches that look up to date")
    x.set_defaults(func=cmd_fantasy_compute)
    x = pf.add_parser("validate", help="check 2026 totals vs 40 published Dream11 totals")
    x.add_argument("--full", action="store_true")
    x.set_defaults(func=cmd_fantasy_validate)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
