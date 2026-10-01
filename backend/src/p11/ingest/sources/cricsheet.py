"""Cricsheet JSON (data_version 1.x) adapter: download + pure parsing.

Parsing never resolves players by name against our DB: every name is mapped through the
match's own ``info.registry.people`` (name -> Cricsheet identifier = ``player.id``).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

SOURCE = "cricsheet"
BASE_URL = "https://cricsheet.org"
REGISTER_FILES = ("people.csv", "names.csv")
EXTRA_KINDS = ("wides", "noballs", "byes", "legbyes", "penalty")
# Dismissals that do not count as a wicket for the batting side.
NOT_OUT_KINDS = {"retired hurt", "retired not out"}


# --------------------------------------------------------------------------- download
def download(url: str, dest: Path, timeout: float = 120.0) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    tmp.replace(dest)
    return dest


def download_zip(name: str, dest_dir: Path) -> Path:
    """name: 'ipl_json' | 'recently_added_2_json' | ... (cricsheet.org/downloads/<name>.zip)."""
    name = name.removesuffix(".zip")
    return download(f"{BASE_URL}/downloads/{name}.zip", dest_dir / f"{name}.zip")


def download_register(dest_dir: Path) -> list[Path]:
    return [download(f"{BASE_URL}/register/{f}", dest_dir / f) for f in REGISTER_FILES]


# --------------------------------------------------------------------------- reading
@dataclass(frozen=True)
class RawFile:
    member: str  # file name inside the zip, e.g. "1529281.json"
    data: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    @property
    def match_id(self) -> int:
        return int(Path(self.member).stem)


def iter_zip(path: Path) -> Iterator[RawFile]:
    with zipfile.ZipFile(path) as z:
        for n in sorted(z.namelist()):
            if n.endswith(".json"):
                yield RawFile(n, z.read(n))


# --------------------------------------------------------------------------- parsed model
@dataclass
class ParsedInnings:
    innings: int
    team: str
    super_over: bool
    target_runs: int | None
    target_overs: Decimal | None
    absent_hurt: list[str]  # player ids
    miscounted_overs: bool


@dataclass
class ParsedMatch:
    match_id: int
    revision: int | None
    data_version: str
    event_name: str
    season_label: str
    season_year: int
    start_date: dt.date
    venue: str | None
    city: str | None
    teams: list[str]
    toss_winner: str | None
    toss_decision: str | None
    result: str  # win|tie|no_result
    winner: str | None
    win_by_runs: int | None
    win_by_wickets: int | None
    method: str | None
    match_number: int | None
    stage: str | None
    overs: int
    balls_per_over: int
    player_of_match: list[str]
    innings: list[ParsedInnings]
    players: list[dict[str, Any]]  # {player_id, team, role_in_match}
    deliveries: list[dict[str, Any]]
    # names that could not be mapped through info.registry.people (DQ failure)
    unresolved_names: set[str] = field(default_factory=set)
    multi_wicket_balls: list[tuple[int, int]] = field(default_factory=list)
    team_players: dict[str, list[str]] = field(default_factory=dict)  # team -> ids (info.players)
    impact_ins: dict[str, int] = field(default_factory=dict)  # team -> match replacements in

    def facts(self) -> dict[str, Any]:
        """This source's match-level view (stored per source in match_source.facts)."""
        return {
            "teams": self.teams,
            "venue": self.venue,
            "city": self.city,
            "start_date": self.start_date.isoformat(),
            "toss_winner": self.toss_winner,
            "toss_decision": self.toss_decision,
            "result": self.result,
            "winner": self.winner,
            "win_by_runs": self.win_by_runs,
            "win_by_wickets": self.win_by_wickets,
            "method": self.method,
            "match_number": self.match_number,
            "stage": self.stage,
            "player_of_match": self.player_of_match,
        }


def parse_bytes(data: bytes, match_id: int) -> ParsedMatch:
    return parse_match(json.loads(data), match_id)


def parse_match(doc: dict[str, Any], match_id: int) -> ParsedMatch:
    info = doc["info"]
    meta = doc.get("meta", {})
    reg: dict[str, str] = info.get("registry", {}).get("people", {})
    unresolved: set[str] = set()

    def pid(name: str) -> str:
        p = reg.get(name)
        if p is None:
            unresolved.add(name)
            return f"?{name}"
        return p

    event = info.get("event", {})
    outcome = info.get("outcome", {})
    dates = sorted(info["dates"])
    start = dt.date.fromisoformat(dates[0])
    by = outcome.get("by", {})
    if "winner" in outcome:
        result, winner = "win", outcome["winner"]
    elif outcome.get("result") == "tie":
        result, winner = "tie", outcome.get("eliminator") or outcome.get("bowl_out")
    else:
        result, winner = "no_result", None
    toss = info.get("toss", {})

    teams: list[str] = list(info["teams"])
    team_players = {t: [pid(n) for n in info.get("players", {}).get(t, [])] for t in teams}

    # roles: everybody listed is XI unless the match-level replacements say otherwise
    roles: dict[str, tuple[str, str]] = {}  # player_id -> (team, role)
    for t, ids in team_players.items():
        for p in ids:
            roles[p] = (t, "xi")
    impact_ins = dict.fromkeys(teams, 0)

    innings_out: list[ParsedInnings] = []
    deliveries: list[dict[str, Any]] = []
    multi: list[tuple[int, int]] = []
    sub_fielders: dict[str, str] = {}
    for idx, inn in enumerate(doc.get("innings", []), start=1):
        bat_team = inn["team"]
        bowl_team = next((t for t in teams if t != bat_team), bat_team)
        tgt = inn.get("target") or {}
        innings_out.append(
            ParsedInnings(
                innings=idx,
                team=bat_team,
                super_over=bool(inn.get("super_over", False)),
                target_runs=tgt.get("runs"),
                target_overs=Decimal(str(tgt["overs"])) if "overs" in tgt else None,
                absent_hurt=[pid(n) for n in inn.get("absent_hurt", [])],
                miscounted_overs=bool(inn.get("miscounted_overs")),
            )
        )
        seq = 0
        for over in inn.get("overs", []):
            for bi, d in enumerate(over["deliveries"], start=1):
                seq += 1
                for rep in d.get("replacements", {}).get("match", []):
                    team = rep.get("team", bat_team)
                    reason = rep.get("reason")
                    pin, pout = pid(rep["in"]), pid(rep["out"])
                    impact_ins[team] = impact_ins.get(team, 0) + 1
                    if reason == "impact_player":
                        roles[pin] = (team, "impact_in")
                        roles[pout] = (team, "impact_out")
                    else:  # concussion_substitute etc.
                        roles[pin] = (team, "sub")
                ex = d.get("extras", {})
                runs = d["runs"]
                wk = d.get("wickets", [])
                if len(wk) > 1:
                    multi.append((idx, seq))
                w = wk[0] if wk else {}
                fielders = []
                for f in w.get("fielders", []):
                    if "name" not in f:
                        continue
                    fid = pid(f["name"])
                    fielders.append(fid)
                    if f.get("substitute"):
                        sub_fielders.setdefault(fid, bowl_team)
                extra_type = next((k for k in EXTRA_KINDS if k in ex), None)
                deliveries.append(
                    {
                        "innings": idx,
                        "ball_seq": seq,
                        "super_over": bool(inn.get("super_over", False)),
                        "over": over["over"],
                        "ball_in_over": bi,
                        "batter_id": pid(d["batter"]),
                        "bowler_id": pid(d["bowler"]),
                        "non_striker_id": pid(d["non_striker"]),
                        "batter_runs": runs["batter"],
                        "extras": runs["extras"],
                        "total_runs": runs["total"],
                        "extra_type": extra_type,
                        **{k: int(ex.get(k, 0)) for k in EXTRA_KINDS},
                        "non_boundary": bool(runs.get("non_boundary", False)),
                        "wicket_kind": w.get("kind"),
                        "player_out_id": pid(w["player_out"]) if w else None,
                        "fielder_ids": fielders or None,
                    }
                )
    for fid, team in sub_fielders.items():
        roles.setdefault(fid, (team, "sub_fielder"))

    players = [
        {"player_id": p, "team": t, "role_in_match": r} for p, (t, r) in sorted(roles.items())
    ]
    season_label = str(info["season"])
    return ParsedMatch(
        match_id=match_id,
        revision=meta.get("revision"),
        data_version=str(meta.get("data_version", "")),
        event_name=event.get("name", "unknown"),
        season_label=season_label,
        season_year=start.year,
        start_date=start,
        venue=info.get("venue"),
        city=info.get("city"),
        teams=teams,
        toss_winner=toss.get("winner"),
        toss_decision=toss.get("decision"),
        result=result,
        winner=winner,
        win_by_runs=by.get("runs"),
        win_by_wickets=by.get("wickets"),
        method=outcome.get("method"),
        match_number=event.get("match_number"),
        stage=event.get("stage"),
        overs=int(info.get("overs", 20)),
        balls_per_over=int(info.get("balls_per_over", 6)),
        player_of_match=[pid(n) for n in info.get("player_of_match", [])],
        innings=innings_out,
        players=players,
        deliveries=deliveries,
        unresolved_names=unresolved,
        multi_wicket_balls=multi,
        team_players=team_players,
        impact_ins=impact_ins,
    )
