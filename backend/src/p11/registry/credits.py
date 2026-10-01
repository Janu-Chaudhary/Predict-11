"""Dream11 credits: squad CSVs -> season_credits, plus the query-time season fallback.

Input: data/raw/Teams/<team-slug>_squad.csv (owner-supplied). Header quirks handled: the credit
column is called credits/Credit/Credits/Credit Points, one file has a UTF-8 BOM, and
``Full Name`` holds Cricsheet-style names (sometimes with stray spaces).

Matching never goes global: a row can only match a player who appeared for *that team* in the
surrounding seasons (season-1 .. season+1), by exact (normalised) name/unique_name/alias.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Connection, text

from p11.core.upsert import Changes, upsert

from .canonical import Resolver

# Owner decision 2026-10-02: 2025 credits stand in for 2026 until 2026 credits are supplied.
# Applied at query time only (no duplicated rows); once season 2026 rows exist they win.
CREDITS_FALLBACK: dict[int, int] = {2026: 2025}


_NUM = re.compile(r"^\d+(\.\d+)?$")
_CREDIT_AND_NAME = re.compile(r"^(?P<credits>\d+(\.\d+)?)\s*(?P<name>[A-Za-z].*)$")


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace(".", " ").strip()).casefold()


def initial_surname_match(display: str, cricsheet_name: str) -> bool:
    """Same surname, and the Cricsheet first token is either initials starting with the display
    first name's letter ('Manav Suthar' ~ 'MJ Suthar') or a near-identical first name sharing
    its first 4 letters ('Mohammad Shami' ~ 'Mohammed Shami'). Used only within one team's
    players, only for rows with no exact hit, and only when the hit is unique."""
    a, b = norm(display).split(), cricsheet_name.replace(".", " ").split()
    if len(a) < 2 or len(b) < 2 or a[-1] != b[-1].casefold():
        return False
    first = b[0]
    if first.isupper() and len(first) <= 3:  # initials, e.g. "MJ"
        return first[0].casefold() == a[0][0]
    return len(a[0]) >= 4 and first.casefold()[:4] == a[0][:4]


def team_name_from_file(path: Path) -> str:
    slug = path.stem.removesuffix("_squad")
    return " ".join(w.capitalize() for w in slug.split("-"))


@dataclass
class CreditRow:
    team: str
    name: str
    full_name: str
    credits: Decimal | None  # None: blank in the CSV (reported, not loaded)
    file: str


def read_team_csv(path: Path) -> list[CreditRow]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        fields = rd.fieldnames or []
        credit_col = next((c for c in fields if "credit" in c.strip().lower()), None)
        if credit_col is None:
            raise ValueError(f"{path.name}: no credits column in {fields}")
        out = []
        for r in rd:
            raw = (r.get(credit_col) or "").strip()
            full = (r.get("Full Name") or "").strip()
            # a row with a missing comma: credit column holds "6.5K Khejroliya", Full Name empty
            m = _CREDIT_AND_NAME.match(raw)
            if m and not full:
                raw, full = m["credits"], m["name"].strip()
            out.append(
                CreditRow(
                    team=team_name_from_file(path),
                    name=(r.get("Name") or "").strip(),
                    full_name=full,
                    credits=Decimal(raw) if _NUM.match(raw) else None,
                    file=path.name,
                )
            )
        return out


@dataclass
class CreditsReport:
    season: int
    rows: int = 0
    matched: int = 0
    unmatched: list[CreditRow] = field(default_factory=list)
    ambiguous: list[tuple[CreditRow, list[str]]] = field(default_factory=list)
    duplicates: list[tuple[CreditRow, str]] = field(default_factory=list)
    no_credits: list[CreditRow] = field(default_factory=list)
    fuzzy: list[tuple[CreditRow, str]] = field(default_factory=list)  # owner should eyeball
    changes: Changes = field(default_factory=Changes)


def _team_candidates(
    conn: Connection, team_id: int, years: tuple[int, int]
) -> list[tuple[str, str]]:
    """(player id, any known name) for players who played for the team in ``years``."""
    rows = conn.execute(
        text(
            """
            WITH pl AS (
              SELECT DISTINCT mp.player_id
              FROM match_player_resolved mp
              JOIN match m ON m.id = mp.match_id
              JOIN season s ON s.id = m.season_id
              WHERE mp.team_id = :t AND s.year BETWEEN :y0 AND :y1
            )
            SELECT p.id, p.name FROM pl JOIN player p ON p.id = pl.player_id
            UNION SELECT p.id, p.unique_name FROM pl JOIN player p ON p.id = pl.player_id
            UNION SELECT a.player_id, a.name FROM pl JOIN player_alias a USING (player_id)
            """
        ),
        {"t": team_id, "y0": years[0], "y1": years[1]},
    )
    return [(r[0], r[1]) for r in rows]


def load_credits(conn: Connection, teams_dir: Path, season: int) -> CreditsReport:
    rep = CreditsReport(season=season)
    resolver = Resolver(conn)
    out: dict[str, dict] = {}
    pending: list[tuple[CreditRow, int, list[tuple[str, str]]]] = []

    def take(r: CreditRow, team_id: int, pid: str) -> bool:
        if pid in out:
            rep.duplicates.append((r, pid))
            return False
        out[pid] = {
            "season": season,
            "player_id": pid,
            "team_id": team_id,
            "credits": r.credits,
            "source": f"Teams/{r.file}",
        }
        rep.matched += 1
        return True

    # pass 1: exact (normalised) name / unique_name / alias within the team
    for path in sorted(teams_dir.glob("*.csv")):
        rows = read_team_csv(path)
        if not rows:
            continue
        team_id = resolver.team(rows[0].team)
        names = _team_candidates(conn, team_id, (season - 1, season + 1))
        exact: dict[str, set[str]] = {}
        for pid, nm in names:
            exact.setdefault(norm(nm), set()).add(pid)
        for r in rows:
            rep.rows += 1
            if r.credits is None:
                rep.no_credits.append(r)
                continue
            hits: set[str] = set()
            for nm in (r.full_name, r.name):
                if nm and (hits := exact.get(norm(nm), set())):
                    break
            if len(hits) == 1:
                take(r, team_id, next(iter(hits)))
            elif hits:
                rep.ambiguous.append((r, sorted(hits)))
            else:
                pending.append((r, team_id, names))
    # pass 2: initial+surname among the team's players not already claimed by an exact match
    for r, team_id, names in pending:
        hits = {
            pid
            for pid, nm in names
            if pid not in out and any(initial_surname_match(d, nm) for d in (r.name, r.full_name))
        }
        if len(hits) == 1:
            pid = next(iter(hits))
            if take(r, team_id, pid):
                rep.fuzzy.append((r, pid))
        elif hits:
            rep.ambiguous.append((r, sorted(hits)))
        else:
            rep.unmatched.append(r)
    rep.changes = upsert(
        conn,
        "season_credits",
        list(out.values()),
        ["season", "player_id"],
        delete_missing=(["season"], [(season,)]),
    )
    return rep


def effective_credits_season(conn: Connection, season: int) -> int | None:
    """The season whose credits apply to ``season`` (itself if loaded, else the fallback)."""
    s: int | None = season
    seen = set()
    while s is not None and s not in seen:
        seen.add(s)
        if conn.execute(
            text("SELECT 1 FROM season_credits WHERE season = :s LIMIT 1"), {"s": s}
        ).first():
            return s
        s = CREDITS_FALLBACK.get(s)
    return None


def credits_for_season(conn: Connection, season: int) -> tuple[int | None, dict[str, Decimal]]:
    """(effective season, {player_id: credits}) for ``season``, applying CREDITS_FALLBACK."""
    eff = effective_credits_season(conn, season)
    if eff is None:
        return None, {}
    rows = conn.execute(
        text("SELECT player_id, credits FROM season_credits WHERE season = :s"), {"s": eff}
    )
    return eff, {r[0]: r[1] for r in rows}
