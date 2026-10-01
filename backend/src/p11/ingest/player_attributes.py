"""Load ``player_attribute`` (+ ``player_media``) from every source we have.

Sources (``player_attribute.source``):
- ``cricinfo``    cached ESPNcricinfo full-scorecard ``__NEXT_DATA__`` (IPL 2026, 74 matches):
                  playingRoles / longBattingStyles / longBowlingStyles; ID = cricinfo objectId.
- ``espn_api``    ESPN core API athlete JSON (``core.espnuk.org/v2/sports/cricket/athletes/<id>``),
                  fetched politely (<= 1 req/s) and cached under data/archive/espn_athletes/.
                  Covers retired players; ID = cricinfo id.
- ``bcci``        official IPL 2026 squads (iplt20 squads_2026.csv) + per-match stats.bcci.tv
                  scorecards (batting_hand, bowling_desc, player_role). BCCI IDs are not in the
                  Cricsheet register, so they are matched by name *within the team's players*.
- ``iplt20_2025`` owner-supplied 2025 squad CSVs (data/raw/Teams, Role column), same matcher.
- ``cricbuzz``    Cricbuzz series squad JSON (one squad cached), cricbuzz id or team matcher.
- ``derived``     role fallback from IPL history (p11.registry.attributes.derive_role).

Media (``player_media``): 2026 squad image URLs (``bcci``) and 2025 headshots (``iplt20_2025``,
data/raw/media/player_images_2025.json, name -> URL, matched within 2025 squads only).
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import time
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import Connection, text

from p11.core.settings import REPO_ROOT, get_settings
from p11.core.upsert import Changes, upsert
from p11.registry.attributes import (
    CareerLine,
    derive_role,
    normalize_batting_hand,
    normalize_bowling_type,
    normalize_role,
)
from p11.registry.canonical import canonical_team_name
from p11.registry.credits import _team_candidates, initial_surname_match, norm, read_team_csv

SPIKES = REPO_ROOT / "spikes"
ESPN_SCORECARDS = SPIKES / "espncricinfo" / "samples" / "raw"
BCCI_SQUADS_CSV = SPIKES / "iplt20" / "samples" / "06" / "squads_2026.csv"
BCCI_RAW = SPIKES / "iplt20" / "samples" / "raw"
BCCI_CROSSWALK = SPIKES / "iplt20" / "bcci_cricsheet_crosswalk.json"
CRICBUZZ_SQUADS = {  # cached series-squad JSON -> team
    SPIKES / "cricbuzz" / "samples" / "06_series_squad_99705.json": "Chennai Super Kings",
}
ESPN_ATHLETE_URL = "http://core.espnuk.org/v2/sports/cricket/athletes/{id}"

ATTR_COLS = ("playing_role", "source_role", "batting_hand", "bowling_style", "bowling_type")


@dataclass
class SourceReport:
    rows: int = 0
    unmatched: list[str] = field(default_factory=list)
    changes: Changes = field(default_factory=Changes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "unmatched": len(self.unmatched),
            "unmatched_sample": self.unmatched[:15],
            "changes": vars(self.changes),
        }


def _row(pid: str, source: str, as_of: dt.date, *, role_raw: Any = None, keeper: bool = False,
         hand_raw: Any = None, bowl_raw: Any = None, detail: dict | None = None) -> dict:
    styles = [bowl_raw] if isinstance(bowl_raw, str) else list(bowl_raw or [])
    styles = [s for s in styles if s]
    roles = [role_raw] if isinstance(role_raw, str) else list(role_raw or [])
    return {
        "player_id": pid,
        "source": source,
        "playing_role": normalize_role(roles, keeper=keeper),
        "source_role": ", ".join(r for r in roles if r) or None,
        "batting_hand": normalize_batting_hand(hand_raw),
        "bowling_style": ", ".join(styles) or None,
        "bowling_type": normalize_bowling_type(styles),
        "as_of": as_of,
        "detail": detail,
    }


def _write(conn: Connection, source: str, rows: dict[str, dict]) -> Changes:
    return upsert(
        conn,
        "player_attribute",
        list(rows.values()),
        ["player_id", "source"],
        delete_missing=(["source"], [(source,)]),
    )


def _cricinfo_map(conn: Connection) -> dict[str, str]:
    rows = conn.execute(
        text("SELECT source_key, player_id FROM player_source_id WHERE source = 'cricinfo'")
    )
    return {r[0]: r[1] for r in rows}


def _team_id(conn: Connection, name: str) -> int | None:
    r = conn.execute(
        text("SELECT team_id FROM team_alias WHERE alias = :a"), {"a": canonical_team_name(name)}
    ).first()
    return r[0] if r else None


# ------------------------------------------------------------------ team-constrained matcher


class TeamMatcher:
    """Name -> player id, only among players who played for that team in the given seasons
    (never global). Pass 1: exact normalised name/unique_name/alias; pass 2: initial+surname,
    unique among players not already claimed."""

    def __init__(self, conn: Connection, years: tuple[int, int]):
        self.conn, self.years = conn, years
        self._cands: dict[int, list[tuple[str, str]]] = {}

    def candidates(self, team_id: int) -> list[tuple[str, str]]:
        if team_id not in self._cands:
            self._cands[team_id] = _team_candidates(self.conn, team_id, self.years)
        return self._cands[team_id]

    def match(self, team_id: int, items: list[tuple[str, list[str]]]) -> dict[str, str]:
        cands = self.candidates(team_id)
        exact: dict[str, set[str]] = defaultdict(set)
        for pid, nm in cands:
            exact[norm(nm)].add(pid)
        out: dict[str, str] = {}
        pending = []
        for key, names in items:
            hits: set[str] = set()
            for nm in names:
                if nm and (hits := exact.get(norm(nm), set())):
                    break
            if len(hits) == 1:
                out[key] = next(iter(hits))
            else:
                pending.append((key, names))
        claimed = set(out.values())
        for key, names in pending:
            hits = {
                pid
                for pid, nm in cands
                if pid not in claimed
                and any(n and initial_surname_match(n, nm) for n in names)
            }
            if len(hits) == 1:
                out[key] = next(iter(hits))
                claimed |= hits
        return out


# ------------------------------------------------------------------ ESPN cached scorecards


def iter_espn_scorecard_players(root: Path = ESPN_SCORECARDS) -> Iterable[tuple[dt.date, dict]]:
    for f in sorted(root.glob("*/full-scorecard.next.json")):
        data = json.loads(f.read_text())["props"]["appPageProps"]["data"]
        day = dt.date.fromisoformat(data["match"]["startDate"][:10])
        for team in data["content"]["matchPlayers"]["teamPlayers"]:
            for p in team["players"]:
                yield day, p["player"]


def load_cricinfo(conn: Connection, root: Path = ESPN_SCORECARDS) -> SourceReport:
    rep = SourceReport()
    ids = _cricinfo_map(conn)
    rows: dict[str, dict] = {}
    for day, p in iter_espn_scorecard_players(root):
        pid = ids.get(str(p["objectId"]))
        if pid is None:
            rep.unmatched.append(f"{p['objectId']} {p.get('longName')}")
            continue
        if pid in rows and rows[pid]["as_of"] >= day:
            continue
        rows[pid] = _row(
            pid, "cricinfo", day,
            role_raw=p.get("playingRoles"),
            hand_raw=p.get("longBattingStyles") or p.get("battingStyles"),
            bowl_raw=p.get("longBowlingStyles") or p.get("bowlingStyles"),
            detail={"cricinfo_id": p["objectId"]},
        )
    rep.rows = len(rows)
    rep.changes = _write(conn, "cricinfo", rows)
    return rep


# ------------------------------------------------------------------ ESPN core API (live)


def espn_cache_dir() -> Path:
    return get_settings().raw_archive_dir / "espn_athletes"


def parse_espn_athlete(doc: dict) -> dict[str, Any]:
    styles = doc.get("styles") or doc.get("style") or []
    pos = doc.get("position") or {}
    return {
        "role_raw": pos.get("name") if isinstance(pos, dict) else None,
        "hand_raw": [s.get("description") for s in styles if s.get("type") == "batting"],
        "bowl_raw": [s.get("description") for s in styles if s.get("type") == "bowling"],
    }


def fetch_espn_athletes(
    cricinfo_ids: Iterable[str], *, min_interval_s: float = 1.0, client: httpx.Client | None = None
) -> dict[str, Any]:
    """Fetch (and cache) athlete JSON for ids not yet cached. <= 1 request per second."""
    cache = espn_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    stats = {"cached": 0, "fetched": 0, "failed": []}
    own = client is None
    client = client or httpx.Client(
        timeout=30, headers={"User-Agent": get_settings().http_user_agent}
    )
    last = 0.0
    try:
        for cid in cricinfo_ids:
            path = cache / f"{cid}.json"
            if path.exists():
                stats["cached"] += 1
                continue
            for attempt in range(3):
                wait = min_interval_s - (time.monotonic() - last)
                if wait > 0:
                    time.sleep(wait)
                last = time.monotonic()
                try:
                    r = client.get(ESPN_ATHLETE_URL.format(id=cid))
                    if r.status_code == 200:
                        doc = json.loads(r.text, strict=False)
                        path.write_text(json.dumps(doc))
                        stats["fetched"] += 1
                        break
                    if r.status_code == 404:
                        stats["failed"].append(f"{cid}: 404")
                        break
                except (httpx.HTTPError, json.JSONDecodeError) as e:
                    if attempt == 2:
                        stats["failed"].append(f"{cid}: {e!r}"[:120])
                    time.sleep(2 * (attempt + 1))
            else:
                stats["failed"].append(f"{cid}: gave up")
    finally:
        if own:
            client.close()
    return stats


def ipl_player_cricinfo_ids(conn: Connection) -> dict[str, str]:
    """cricinfo id -> player id for every player who appeared in an IPL match."""
    rows = conn.execute(
        text(
            """
            SELECT DISTINCT s.source_key, s.player_id
            FROM match_player_resolved mp
            JOIN player_source_id s ON s.player_id = mp.player_id AND s.source = 'cricinfo'
            """
        )
    )
    return {r[0]: r[1] for r in rows}


def load_espn_api(conn: Connection, *, fetch: bool = False) -> tuple[SourceReport, dict]:
    rep = SourceReport()
    ids = ipl_player_cricinfo_ids(conn)
    fetch_stats: dict[str, Any] = {}
    if fetch:
        # only players the cached 2026 scorecards don't already describe
        have = {
            r[0]
            for r in conn.execute(
                text("SELECT player_id FROM player_attribute WHERE source = 'cricinfo'")
            )
        }
        fetch_stats = fetch_espn_athletes(
            sorted((c for c, p in ids.items() if p not in have), key=int)
        )
    cache = espn_cache_dir()
    rows: dict[str, dict] = {}
    for cid, pid in ids.items():
        path = cache / f"{cid}.json"
        if not path.exists():
            rep.unmatched.append(f"{cid} (not fetched)")
            continue
        doc = json.loads(path.read_text())
        p = parse_espn_athlete(doc)
        as_of = dt.date.fromtimestamp(path.stat().st_mtime)
        rows[pid] = _row(pid, "espn_api", as_of, detail={"cricinfo_id": int(cid)}, **p)
    rep.rows = len(rows)
    rep.changes = _write(conn, "espn_api", rows)
    return rep, fetch_stats


# ------------------------------------------------------------------ BCCI (official 2026)


@dataclass
class BcciPerson:
    bcci_id: str
    team: str
    names: list[str] = field(default_factory=list)
    role: str | None = None
    keeper: bool = False
    hand: str | None = None
    bowling: str | None = None
    image: str | None = None
    season: int = 2026


def read_bcci_people(
    squads_csv: Path = BCCI_SQUADS_CSV, raw_dir: Path = BCCI_RAW
) -> dict[str, BcciPerson]:
    people: dict[str, BcciPerson] = {}
    if squads_csv.exists():
        with squads_csv.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                team = " ".join(w.capitalize() for w in r["team"].split("-"))
                # epr_role 'undefined' rows carry a placeholder 'batsman' role (e.g. the
                # left-arm wrist spinner Vignesh Puthur): don't trust it.
                role = None if r.get("epr_role") == "undefined" else r["role"]
                people[r["player_id"]] = BcciPerson(
                    r["player_id"], team, [r["short_name"], r["name"]], role,
                    image=r.get("image") or None,
                )
    for f in sorted(raw_dir.glob("*/scorecard.json")):
        try:
            doc = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        if str(doc.get("match", {}).get("comp_season")) != "2026":
            continue
        for t in doc.get("team", []):
            for p in t.get("player", []):
                bid = str(p["player_id"])
                person = people.get(bid)
                if person is None:
                    person = people[bid] = BcciPerson(
                        bid, t["name"], [], p.get("player_role"),
                    )
                for nm in (p.get("known_as"), p.get("name")):
                    if nm and nm not in person.names:
                        person.names.append(nm)
                person.hand = person.hand or p.get("batting_hand")
                person.bowling = person.bowling or p.get("bowling_desc")
                if person.role is None and p.get("player_role") not in (None, "", "undefined"):
                    person.role = p.get("player_role")
    return people


def load_bcci(conn: Connection) -> tuple[SourceReport, dict[str, str]]:
    """Returns the report and the bcci id -> player id bridge it built."""
    rep = SourceReport()
    people = read_bcci_people()
    crosswalk: dict[str, str] = {}
    if BCCI_CROSSWALK.exists():
        crosswalk = json.loads(BCCI_CROSSWALK.read_text())
    matcher = TeamMatcher(conn, (2025, 2026))
    by_team: dict[int, list[tuple[str, list[str]]]] = defaultdict(list)
    for p in people.values():
        tid = _team_id(conn, p.team)
        if tid is None:
            continue  # reported below as unmatched
        names = ([crosswalk[p.bcci_id]] if p.bcci_id in crosswalk else []) + p.names
        by_team[tid].append((p.bcci_id, names))
    bridge: dict[str, str] = {}
    for tid, items in by_team.items():
        bridge.update(matcher.match(tid, items))
    rows: dict[str, dict] = {}
    media: dict[str, dict] = {}
    as_of = dt.date(2026, 3, 28)  # IPL 2026 squads as at the season start
    for bid, p in people.items():
        pid = bridge.get(bid)
        if pid is None:
            rep.unmatched.append(f"{bid} {p.names[:1]} ({p.team})")
            continue
        rows[pid] = _row(
            pid, "bcci", as_of, role_raw=p.role, hand_raw=p.hand, bowl_raw=p.bowling,
            detail={"bcci_id": bid},
        )
        if p.image:
            media[pid] = {"player_id": pid, "source": "bcci", "image_url": p.image,
                          "image_season": 2026}
    rep.rows = len(rows)
    rep.changes = _write(conn, "bcci", rows)
    rep.changes += upsert(conn, "player_media", list(media.values()), ["player_id", "source"],
                          delete_missing=(["source"], [("bcci",)]))
    return rep, bridge


# ------------------------------------------------------------------ iplt20 2025 squads + media


def load_iplt20_2025(
    conn: Connection, teams_dir: Path | None = None, images: Path | None = None
) -> SourceReport:
    rep = SourceReport()
    data = get_settings().data_dir
    teams_dir = teams_dir or data / "raw" / "Teams"
    images = images or data / "raw" / "media" / "player_images_2025.json"
    matcher = TeamMatcher(conn, (2024, 2026))
    rows: dict[str, dict] = {}
    name_to_pid: dict[str, set[str]] = defaultdict(set)
    for path in sorted(teams_dir.glob("*.csv")):
        roles = {}
        with path.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                roles[(r.get("Name") or "").strip()] = (r.get("Role") or "").strip()
        squad = read_team_csv(path)
        if not squad:
            continue
        tid = _team_id(conn, squad[0].team)
        if tid is None:
            rep.unmatched.append(f"team {squad[0].team}")
            continue
        hits = matcher.match(tid, [(r.name, [r.full_name, r.name]) for r in squad])
        for r in squad:
            pid = hits.get(r.name)
            if pid is None:
                rep.unmatched.append(f"{r.team}: {r.name}")
                continue
            name_to_pid[norm(r.name)].add(pid)
            rows[pid] = _row(pid, "iplt20_2025", dt.date(2025, 3, 22), role_raw=roles.get(r.name),
                             detail={"team": r.team, "name": r.name})
    rep.rows = len(rows)
    rep.changes = _write(conn, "iplt20_2025", rows)

    media: dict[str, dict] = {}
    if images.exists():
        imgs: dict[str, str] = json.loads(images.read_text())
        # fallback matcher: every team's 2025 players (still season-constrained, never global)
        season_matchers = TeamMatcher(conn, (2025, 2025))
        team_ids = [r[0] for r in conn.execute(text(
            "SELECT DISTINCT mp.team_id FROM match_player_resolved mp JOIN match m ON "
            "m.id = mp.match_id JOIN season s ON s.id = m.season_id WHERE s.year = 2025"))]
        for name, url in imgs.items():
            pids = name_to_pid.get(norm(name), set())
            if len(pids) != 1:
                found = set()
                for tid in team_ids:
                    if (h := season_matchers.match(tid, [(name, [name])]).get(name)):
                        found.add(h)
                pids = found
            if len(pids) == 1:
                pid = next(iter(pids))
                media[pid] = {"player_id": pid, "source": "iplt20_2025", "image_url": url,
                              "image_season": 2025}
            else:
                rep.unmatched.append(f"image {name} ({len(pids)} hits)")
    rep.changes += upsert(conn, "player_media", list(media.values()), ["player_id", "source"],
                          delete_missing=(["source"], [("iplt20_2025",)]))
    return rep


# ------------------------------------------------------------------ Cricbuzz


def load_cricbuzz(conn: Connection) -> SourceReport:
    rep = SourceReport()
    cb_ids = {
        r[0]: r[1]
        for r in conn.execute(
            text("SELECT source_key, player_id FROM player_source_id WHERE source = 'cricbuzz'")
        )
    }
    matcher = TeamMatcher(conn, (2025, 2026))
    rows: dict[str, dict] = {}
    for path, team in CRICBUZZ_SQUADS.items():
        if not path.exists():
            continue
        players = [p for p in json.loads(path.read_text())["player"] if not p.get("isHeader")]
        tid = _team_id(conn, team)
        hits = matcher.match(tid, [(p["id"], [p["name"]]) for p in players]) if tid else {}
        for p in players:
            pid = cb_ids.get(p["id"]) or hits.get(p["id"])
            if pid is None:
                rep.unmatched.append(f"{team}: {p['name']}")
                continue
            rows[pid] = _row(pid, "cricbuzz", dt.date(2026, 3, 28), role_raw=p.get("role"),
                             hand_raw=p.get("battingStyle"), bowl_raw=p.get("bowlingStyle"),
                             detail={"cricbuzz_id": p["id"]})
    rep.rows = len(rows)
    rep.changes = _write(conn, "cricbuzz", rows)
    return rep


# ------------------------------------------------------------------ derived from history

CAREER_SQL = """
WITH apps AS (
  SELECT player_id, count(DISTINCT match_id) AS matches, max(m.start_date) AS last_match
  FROM match_player_resolved mp JOIN match m ON m.id = mp.match_id
  WHERE role_in_match IN ('xi', 'impact_in', 'impact_out', 'sub')
  GROUP BY player_id
), bat AS (
  SELECT batter_id AS player_id, count(*) FILTER (WHERE wides = 0) AS faced
  FROM delivery_resolved WHERE NOT super_over GROUP BY 1
), bowl AS (
  SELECT bowler_id AS player_id, count(*) FILTER (WHERE wides = 0 AND noballs = 0) AS balls
  FROM delivery_resolved WHERE NOT super_over GROUP BY 1
), st AS (
  SELECT fielder_ids[1] AS player_id, count(*) AS stumpings
  FROM delivery_resolved WHERE wicket_kind = 'stumped' AND fielder_ids IS NOT NULL GROUP BY 1
)
SELECT a.player_id, a.matches, a.last_match, coalesce(bat.faced, 0), coalesce(bowl.balls, 0),
       coalesce(st.stumpings, 0)
FROM apps a LEFT JOIN bat USING (player_id) LEFT JOIN bowl USING (player_id)
LEFT JOIN st USING (player_id)
"""


def career_lines(conn: Connection) -> dict[str, tuple[CareerLine, dt.date]]:
    return {
        r[0]: (CareerLine(r[1], r[3], r[4], r[5]), r[2]) for r in conn.execute(text(CAREER_SQL))
    }


def load_derived(conn: Connection) -> SourceReport:
    rep = SourceReport()
    rows: dict[str, dict] = {}
    for pid, (c, last) in career_lines(conn).items():
        role = derive_role(c)
        if role is None:
            continue
        rows[pid] = {
            "player_id": pid, "source": "derived", "playing_role": role, "source_role": None,
            "batting_hand": None, "bowling_style": None, "bowling_type": None, "as_of": last,
            "detail": {"matches": c.matches, "balls_faced": c.balls_faced,
                       "legal_balls_bowled": c.legal_balls_bowled, "stumpings": c.stumpings},
        }
    rep.rows = len(rows)
    rep.changes = _write(conn, "derived", rows)
    return rep


def derived_accuracy(conn: Connection) -> dict[str, Any]:
    """How well the history fallback agrees with the best scraped role (players with both)."""
    rows = conn.execute(
        text(
            """
            SELECT d.playing_role, r.playing_role
            FROM player_attribute d
            JOIN LATERAL (
              SELECT a.playing_role FROM player_attribute a
              WHERE a.player_id = d.player_id AND a.source <> 'derived'
                AND a.playing_role IS NOT NULL
              ORDER BY array_position(CAST(:prio AS text[]), a.source) LIMIT 1
            ) r ON true
            WHERE d.source = 'derived'
            """
        ),
        {"prio": ["bcci", "iplt20_2025", "cricinfo", "espn_api", "cricbuzz"]},
    ).all()
    n = len(rows)
    exact = sum(1 for d, r in rows if d == r)
    bowl = sum(1 for d, r in rows if (d == "BOWL") == (r == "BOWL"))
    return {
        "players": n,
        "exact_role_pct": round(100 * exact / n, 1) if n else None,
        "bowl_vs_nonbowl_pct": round(100 * bowl / n, 1) if n else None,
    }


# ------------------------------------------------------------------ orchestration + coverage


def load_all(conn: Connection, *, fetch_espn: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {}
    t0 = time.monotonic()
    out["cricinfo"] = load_cricinfo(conn).as_dict()
    espn, fstats = load_espn_api(conn, fetch=fetch_espn)
    out["espn_api"] = espn.as_dict() | ({"fetch": fstats | {"failed": fstats["failed"][:10]}}
                                        if fstats else {})
    bcci, bridge = load_bcci(conn)
    out["bcci"] = bcci.as_dict() | {"bcci_ids_bridged": len(bridge)}
    out["iplt20_2025"] = load_iplt20_2025(conn).as_dict()
    out["cricbuzz"] = load_cricbuzz(conn).as_dict()
    out["derived"] = load_derived(conn).as_dict()
    out["derived_accuracy"] = derived_accuracy(conn)
    out["seconds"] = round(time.monotonic() - t0, 1)
    return out


COVERAGE_SQL = """
WITH pl AS (
  SELECT DISTINCT mp.player_id
  FROM match_player_resolved mp JOIN match m ON m.id = mp.match_id
  JOIN season s ON s.id = m.season_id
  WHERE mp.role_in_match IN ('xi', 'impact_in', 'impact_out', 'sub')
    AND s.year BETWEEN :y0 AND :y1
), bowled AS (
  SELECT DISTINCT bowler_id AS player_id FROM delivery_resolved
)
SELECT count(*) AS players,
  count(r.playing_role) AS with_role,
  count(r.playing_role) FILTER (WHERE r.role_source <> 'derived') AS with_scraped_role,
  count(r.batting_hand) AS with_batting_hand,
  count(r.bowling_type) AS with_bowling_type,
  count(*) FILTER (WHERE b.player_id IS NOT NULL) AS bowlers,
  count(r.bowling_type) FILTER (WHERE b.player_id IS NOT NULL) AS bowlers_with_type
FROM pl LEFT JOIN player_attribute_resolved r USING (player_id)
LEFT JOIN bowled b USING (player_id)
"""


def coverage(conn: Connection) -> dict[str, Any]:
    def pct(a: int, b: int) -> float:
        return round(100 * a / b, 1) if b else 0.0

    out = {}
    for label, yrs in (("ipl_2024_2026", (2024, 2026)), ("all_ipl", (1900, 2100))):
        r = conn.execute(text(COVERAGE_SQL), {"y0": yrs[0], "y1": yrs[1]}).mappings().one()
        out[label] = {
            "players": r["players"],
            "role_pct": pct(r["with_role"], r["players"]),
            "scraped_role_pct": pct(r["with_scraped_role"], r["players"]),
            "batting_hand_pct": pct(r["with_batting_hand"], r["players"]),
            "bowling_type_pct": pct(r["with_bowling_type"], r["players"]),
            "bowling_type_pct_of_bowlers": pct(r["bowlers_with_type"], r["bowlers"]),
        }
    r = conn.execute(
        text(
            """
            WITH pl AS (
              SELECT DISTINCT mp.player_id FROM match_player_resolved mp
              JOIN match m ON m.id = mp.match_id JOIN season s ON s.id = m.season_id
              WHERE s.year = 2026 AND mp.role_in_match IN ('xi','impact_in','impact_out','sub'))
            SELECT count(*), count(md.image_url),
                   count(*) FILTER (WHERE md.image_source = 'bcci')
            FROM pl LEFT JOIN player_media_resolved md USING (player_id)
            """
        )
    ).one()
    out["photos_2026_xi"] = {"players": r[0], "with_photo_pct": pct(r[1], r[0]),
                             "from_2026_squads": r[2]}
    return out
