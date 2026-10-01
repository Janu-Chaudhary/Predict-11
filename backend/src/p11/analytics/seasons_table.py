"""IPL league-stage points table (F1), pure computation over resolved match rows.

Points: win 2 (a tie settled by super over / boundary count is a win for the winner), no
result 1 each, loss 0. A tie with no recorded winner gives 1 each. Ranking: points, then
wins, then NRR (IPL tie-break order). NRR follows ``seasons_nrr``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from .seasons_data import MatchRow
from .seasons_nrr import InningsFigures, NrrAccumulator, regulation_figures

POINTS_WIN = 2
POINTS_NR = 1


def match_figures(m: MatchRow) -> list[tuple[int, InningsFigures]]:
    """(batting team, figures) for the regulation innings of ``m``."""
    inn1 = next((i for i in m.innings if i.innings == 1), None)
    inn2 = next((i for i in m.innings if i.innings == 2), None)
    if inn1 is None:
        return []
    f1, f2 = regulation_figures(
        (inn1.runs, inn1.legal_balls, inn1.wickets, inn1.absent_hurt),
        (inn2.runs, inn2.legal_balls, inn2.wickets, inn2.absent_hurt) if inn2 else None,
        m.overs,
        inn2.target_runs if inn2 else None,
        inn2.target_overs if inn2 else None,
    )
    out: list[tuple[int, InningsFigures]] = []
    if f1 is not None:
        out.append((inn1.team_id, f1))
    if inn2 is not None and f2 is not None:
        out.append((inn2.team_id, f2))
    return out


@dataclass
class Standing:
    team_id: int
    played: int = 0
    won: int = 0
    lost: int = 0
    no_result: int = 0
    tied: int = 0
    points: int = 0
    nrr: NrrAccumulator = field(default_factory=NrrAccumulator)
    results: list[str] = field(default_factory=list)  # chronological W/L/N
    position: int = 0

    @property
    def sort_key(self) -> tuple[int, int, float, int]:
        return (-self.points, -self.won, -round(self.nrr.nrr, 6), self.team_id)


def compute_standings(matches: Iterable[MatchRow]) -> list[Standing]:
    """Standings from league matches given in chronological order."""
    table: dict[int, Standing] = {}

    def st(team_id: int) -> Standing:
        return table.setdefault(team_id, Standing(team_id))

    for m in matches:
        a, b = st(m.team1_id), st(m.team2_id)
        a.played += 1
        b.played += 1
        if m.result == "no_result":
            for s in (a, b):
                s.no_result += 1
                s.points += POINTS_NR
                s.results.append("N")
            continue
        if m.result == "tie":
            a.tied += 1
            b.tied += 1
        if m.winner_id in (m.team1_id, m.team2_id):
            w, lo = (a, b) if m.winner_id == m.team1_id else (b, a)
            w.won += 1
            w.points += POINTS_WIN
            w.results.append("W")
            lo.lost += 1
            lo.results.append("L")
        else:  # tie without a decider
            for s in (a, b):
                s.points += POINTS_NR
                s.results.append("N")
        for team_id, fig in match_figures(m):
            st(team_id).nrr.add_batting(fig)
            st(m.opponent(team_id)).nrr.add_bowling(fig)

    rows = sorted(table.values(), key=lambda s: s.sort_key)
    for pos, s in enumerate(rows, start=1):
        s.position = pos
    return rows
