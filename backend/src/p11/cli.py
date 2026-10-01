"""`p11` command-line entrypoint. Subcommands are added as phases land."""

from __future__ import annotations

import argparse


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("p11.api.app:app", host=args.host, port=args.port, reload=args.reload)


def main() -> None:
    p = argparse.ArgumentParser(prog="p11")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("serve", help="run the API")
    ps.add_argument("--host", default="127.0.0.1")
    ps.add_argument("--port", type=int, default=8000)
    ps.add_argument("--reload", action="store_true")
    ps.set_defaults(func=cmd_serve)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
