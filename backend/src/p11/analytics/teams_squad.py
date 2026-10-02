"""Team squad ("latest roster") for /teams/{id}/squad.

Owner decision 2026-10-02: the squad is everyone who played for the team in the latest season
of the data, plus players on the team's squad CSV (season_credits for the effective credits
season, e.g. 2025 for 2026) who did not feature, unless they played for another team in the
latest season (moved on). Role from player_attribute_resolved (else the role most used in
lineups is unknown, so BAT); overseas from the squad CSV.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field
from sqlalchemy import Connection, text

from ..registry.credits import effective_credits_season
from . import seasons_data
from .players_identity import player_refs, ref_or_id
from .players_models import PlayerRef
from .seasons_refs import team_ref
from .seasons_schemas import TeamRef

ROLE_ORDER = {"BAT": 0, "WK": 1, "AR": 2, "BOWL": 3}


class NotFound(LookupError):
    pass


class SquadPlayer(BaseModel):
    player: PlayerRef
    role: str = Field(description="WK | BAT | AR | BOWL")
    overseas: bool | None = Field(description="From the squad CSV; null when unknown")
    credits: float | None
    matches: int = Field(description="Matches for this team in the season")
    in_squad_list: bool = Field(description="On the team's squad CSV")


class TeamSquad(BaseModel):
    team: TeamRef
    season: int
    credits_season: int | None
    players: list[SquadPlayer]


def squad(conn: Connection, team_id: int) -> TeamSquad:
    core = seasons_data.core()
    if team_id not in core.teams:
        raise NotFound(f"no team {team_id}")
    season = max(core.seasons)
    eff = effective_credits_season(conn, season)
    lineups = conn.execute(
        text(
            """
            SELECT mp.player_id, mp.team_id, count(DISTINCT mp.match_id)
            FROM match_player_resolved mp
            JOIN match m ON m.id = mp.match_id JOIN season s ON s.id = m.season_id
            WHERE s.year = :y
            GROUP BY 1, 2
            """
        ),
        {"y": season},
    ).all()
    played: Counter[str] = Counter()
    elsewhere: set[str] = set()
    for pid, tid, n in lineups:
        if tid == team_id:
            played[pid] += n
        else:
            elsewhere.add(pid)
    listed: dict[str, tuple[float, bool | None]] = {}
    if eff is not None:
        for pid, cr, ovs in conn.execute(
            text(
                "SELECT player_id, credits, overseas FROM season_credits "
                "WHERE season = :s AND team_id = :t"
            ),
            {"s": eff, "t": team_id},
        ):
            listed[pid] = (float(cr), ovs)
    ids = set(played) | {pid for pid in listed if pid not in elsewhere or pid in played}
    if not ids:
        raise NotFound(f"no squad for team {team_id} in {season}")
    roles = dict(
        conn.execute(
            text(
                "SELECT player_id, playing_role FROM player_attribute_resolved "
                "WHERE player_id = ANY(:ids)"
            ),
            {"ids": list(ids)},
        ).all()
    )
    # credits / overseas for players who were not on this team's list (e.g. traded in)
    other: dict[str, tuple[float, bool | None]] = {}
    if eff is not None:
        for pid, cr, ovs in conn.execute(
            text(
                "SELECT player_id, credits, overseas FROM season_credits "
                "WHERE season = :s AND player_id = ANY(:ids)"
            ),
            {"s": eff, "ids": [i for i in ids if i not in listed]},
        ):
            other[pid] = (float(cr), ovs)
    refs = player_refs(conn, ids)
    players = []
    for pid in ids:
        cr, ovs = listed.get(pid) or other.get(pid) or (None, None)
        players.append(
            SquadPlayer(
                player=ref_or_id(refs, pid),
                role=roles.get(pid) or "BAT",
                overseas=ovs,
                credits=cr,
                matches=played.get(pid, 0),
                in_squad_list=pid in listed,
            )
        )
    players.sort(
        key=lambda p: (
            ROLE_ORDER.get(p.role, 9),
            -p.matches,
            -(p.credits or 0),
            p.player.display_name or p.player.name,
        )
    )
    return TeamSquad(
        team=team_ref(core, team_id, season), season=season, credits_season=eff, players=players
    )
