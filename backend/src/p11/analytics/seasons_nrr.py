"""Net run rate maths (IPL playing conditions), pure functions.

Rules implemented:
- NRR = (runs scored / overs faced) - (runs conceded / overs bowled), overs as balls / 6.
- A side bowled out is charged its full quota of overs, not the overs it actually batted.
- The quota is the innings' entitlement: 20 overs normally; the revised overs when the match
  was shortened (rain / DLS). Cricsheet records the revision as the chasing side's
  ``target_overs`` / ``target_runs``.
- In a shortened match with a revised target, the side batting first is credited with
  (target - 1) runs off the revised overs, whatever it actually made (ICC/IPL rule). This
  reproduces the official 2026 table exactly (e.g. LSG v RCB, match 50, 19-over DLS game).
- No-result matches are excluded entirely; tied matches (incl. super-over finishes) count with
  their two regulation innings. Super-over balls never count.

Not modelled (data gap): when a chase is ended by rain and decided on DLS, ICC rules credit the
side batting first with the DLS *par* score at the overs the chasing side faced. Par scores are
not in the data, so that side's actual innings is used instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

ALL_OUT_WICKETS = 10


def overs_to_balls(overs: Decimal | float | int | str) -> int:
    """Cricket notation -> balls: 19.4 -> 118, 9.2 -> 56, 20 -> 120."""
    d = Decimal(str(overs))
    whole = int(d)
    part = int(((d - whole) * 10).to_integral_value())
    if not 0 <= part <= 5:
        raise ValueError(f"invalid overs notation: {overs}")
    return whole * 6 + part


def balls_to_overs(balls: int) -> str:
    """118 -> "19.4"."""
    return f"{balls // 6}.{balls % 6}" if balls % 6 else str(balls // 6)


@dataclass(frozen=True, slots=True)
class InningsFigures:
    """One regulation innings as NRR sees it."""

    runs: int
    legal_balls: int
    wickets: int  # dismissals, excluding retired hurt / retired not out
    quota_balls: int  # entitlement: 120, or revised overs in a shortened match
    absent_hurt: int = 0

    @property
    def all_out(self) -> bool:
        return self.wickets + self.absent_hurt >= ALL_OUT_WICKETS

    @property
    def nrr_balls(self) -> int:
        """Balls charged for NRR: the full quota when bowled out."""
        return max(self.quota_balls, self.legal_balls) if self.all_out else self.legal_balls


def revised_balls(match_overs: int, target_overs: Decimal | None) -> int | None:
    """Revised innings length in balls, or None when the match was full length."""
    if target_overs is None:
        return None
    revised = overs_to_balls(target_overs)
    return revised if revised < match_overs * 6 else None


def regulation_figures(
    first: tuple[int, int, int, int] | None,
    second: tuple[int, int, int, int] | None,
    match_overs: int,
    target_runs: int | None,
    target_overs: Decimal | None,
) -> tuple[InningsFigures | None, InningsFigures | None]:
    """NRR figures for both regulation innings.

    ``first``/``second`` are (runs, legal_balls, wickets, absent_hurt) as scored. In a
    shortened match the chase's quota is the revised length and the first innings is replaced
    by (target - 1) off the revised length.
    """
    revised = revised_balls(match_overs, target_overs)
    quota = revised if revised is not None else match_overs * 6
    f1 = f2 = None
    if first is not None:
        if revised is not None and target_runs is not None:
            f1 = InningsFigures(target_runs - 1, revised, 0, revised)
        else:
            f1 = InningsFigures(first[0], first[1], first[2], match_overs * 6, first[3])
    if second is not None:
        f2 = InningsFigures(second[0], second[1], second[2], quota, second[3])
    return f1, f2


@dataclass(slots=True)
class NrrAccumulator:
    runs_for: int = 0
    balls_for: int = 0
    runs_against: int = 0
    balls_against: int = 0

    def add_batting(self, inn: InningsFigures) -> None:
        self.runs_for += inn.runs
        self.balls_for += inn.nrr_balls

    def add_bowling(self, inn: InningsFigures) -> None:
        self.runs_against += inn.runs
        self.balls_against += inn.nrr_balls

    @property
    def nrr(self) -> float:
        rf = self.runs_for * 6 / self.balls_for if self.balls_for else 0.0
        ra = self.runs_against * 6 / self.balls_against if self.balls_against else 0.0
        return rf - ra

    @property
    def overs_for(self) -> str:
        return balls_to_overs(self.balls_for)

    @property
    def overs_against(self) -> str:
        return balls_to_overs(self.balls_against)
