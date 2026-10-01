"""Versioned Dream11 T20 rule sets. See RULES.md in this package for sources.

Every rule set is a frozen dataclass; nothing in here does any scoring. Rates (strike
rate, economy) are compared as exact ``Fraction`` values so band edges such as
"150.01-170" or "11.01-12" behave exactly at the documented thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from enum import StrEnum
from fractions import Fraction

from p11.scoring.types import Role


class MilestoneMode(StrEnum):
    HIGHEST_ONLY = "highest_only"
    """Only the highest milestone reached is paid (e.g. 80 runs -> 75-run bonus only)."""

    STACK_BELOW_CENTURY = "stack_below_century"
    """Literal reading of Dream11's note: every milestone reached stacks, except that a
    century replaces all lower milestones (80 runs -> 25+50+75 bonuses; 100 -> 100 only)."""


class HaulMode(StrEnum):
    HIGHEST_ONLY = "highest_only"
    STACK = "stack"


@dataclass(frozen=True, slots=True)
class Band:
    """A rate interval -> points. ``None`` bounds are open-ended."""

    points: int
    lo: Fraction | None = None
    lo_inclusive: bool = True
    hi: Fraction | None = None
    hi_inclusive: bool = True

    def contains(self, x: Fraction) -> bool:
        if self.lo is not None and (x < self.lo or (x == self.lo and not self.lo_inclusive)):
            return False
        return not (
            self.hi is not None and (x > self.hi or (x == self.hi and not self.hi_inclusive))
        )


def F(x: str | int) -> Fraction:
    return Fraction(x)


def band_points(bands: tuple[Band, ...], x: Fraction) -> int:
    for b in bands:
        if b.contains(x):
            return b.points
    return 0


# Strike rate (runs per 100 balls), min 10 balls, not for bowlers. Same in all versions.
#   Above 170 +6 | 150.01-170 +4 | 130-150 +2 | 60-70 -2 | 50-59.99 -4 | Below 50 -6
T20_STRIKE_RATE_BANDS: tuple[Band, ...] = (
    Band(6, lo=F(170), lo_inclusive=False),
    Band(4, lo=F(150), lo_inclusive=False, hi=F(170)),
    Band(2, lo=F(130), hi=F(150)),
    Band(-2, lo=F(60), hi=F(70)),
    Band(-4, lo=F(50), hi=F(60), hi_inclusive=False),
    Band(-6, hi=F(50), hi_inclusive=False),
)

# Economy (runs per over), min 2 overs. Same in all versions.
#   Below 5 +6 | 5-5.99 +4 | 6-7 +2 | 10-11 -2 | 11.01-12 -4 | Above 12 -6
T20_ECONOMY_BANDS: tuple[Band, ...] = (
    Band(6, hi=F(5), hi_inclusive=False),
    Band(4, lo=F(5), hi=F(6), hi_inclusive=False),
    Band(2, lo=F(6), hi=F(7)),
    Band(-2, lo=F(10), hi=F(11)),
    Band(-4, lo=F(11), lo_inclusive=False, hi=F(12)),
    Band(-6, lo=F(12), lo_inclusive=False),
)


@dataclass(frozen=True, slots=True)
class RuleSet:
    version: str
    effective_from: date
    # lineup
    announced_lineup: int = 4
    substitute_played: int = 4
    # batting
    run: int = 1
    boundary_bonus: int = 4
    six_bonus: int = 6
    run_milestones: tuple[tuple[int, int], ...] = ((25, 4), (50, 8), (75, 12), (100, 16))
    century_runs: int = 100
    milestone_mode: MilestoneMode = MilestoneMode.HIGHEST_ONLY
    duck: int = -2
    duck_roles: frozenset[Role] = frozenset({Role.BAT, Role.WK, Role.AR})
    strike_rate_min_balls: int = 10
    strike_rate_exempt_roles: frozenset[Role] = frozenset({Role.BOWL})
    strike_rate_bands: tuple[Band, ...] = T20_STRIKE_RATE_BANDS
    # bowling
    dot_ball: int = 1
    dot_ball_counts_byes_legbyes: bool = True
    wicket: int = 30
    lbw_bowled_bonus: int = 8
    wicket_hauls: tuple[tuple[int, int], ...] = ((3, 4), (4, 8), (5, 12))
    haul_mode: HaulMode = HaulMode.HIGHEST_ONLY
    maiden: int = 12
    economy_min_balls: int = 12
    economy_bands: tuple[Band, ...] = T20_ECONOMY_BANDS
    # fielding
    catch: int = 8
    catch_bonus_threshold: int = 3
    catch_bonus: int = 4
    caught_and_bowled_counts_as_catch: bool = True
    stumping: int = 12
    runout_direct: int = 12
    runout_indirect: int = 6
    runout_indirect_max_fielders: int = 2
    # multipliers
    captain_multiplier: float = 2.0
    vice_captain_multiplier: float = 1.5
    # scope
    count_super_over: bool = False
    notes: tuple[str, ...] = field(default=())


T20_2025 = RuleSet(
    version="T20_2025",
    # Verified in force on 2025-04-23 (archived official page). The new batting /
    # dot-ball table was already live on 2025-02-09 with wicket=+25; wicket=+30 appeared
    # between 2025-02-09 and 2025-04-23. IPL 2025 opened 2025-03-22 -> used as the
    # effective date (exact switch date unverified).
    effective_from=date(2025, 3, 22),
    notes=(
        "Source: dream11.com/fantasy-cricket/point-system (archived 2025-04-23)",
        "milestone_mode and haul_mode stacking semantics unverified; see RULES.md",
    ),
)

# IPL 2026: the official page (archived 2026-01-17) and the live how-to-play page
# (fetched 2026-10-02) show values identical to 2025. Kept as its own version so a
# future divergence only needs a new RuleSet.
T20_2026 = replace(
    T20_2025,
    version="T20_2026",
    effective_from=date(2026, 1, 1),
    notes=(
        "Source: dream11.com/fantasy-cricket/point-system (archived 2026-01-17) and "
        "dream11.com/games/fantasy-cricket/how-to-play (fetched 2026-10-02)",
        "Identical values to T20_2025",
    ),
)

# Pre-2025 T20 system (confirmed on archived pages 2024-02-27 .. 2025-01-13).
# Provided for scoring historical matches under the rules that were live at the time.
T20_2024 = RuleSet(
    version="T20_2024",
    effective_from=date(2024, 1, 1),  # start date unverified (confirmed live 2024-02-27)
    boundary_bonus=1,
    six_bonus=2,
    run_milestones=((30, 4), (50, 8), (100, 16)),
    dot_ball=0,
    wicket=25,
    wicket_hauls=((3, 4), (4, 8), (5, 16)),
    notes=("Source: dream11.com/fantasy-cricket/point-system (archived 2024-02-27..2025-01-13)",),
)

RULESETS: dict[str, RuleSet] = {r.version: r for r in (T20_2024, T20_2025, T20_2026)}
DEFAULT_RULESET = T20_2026


def get_ruleset(version: str) -> RuleSet:
    try:
        return RULESETS[version]
    except KeyError as e:
        raise KeyError(f"unknown rule set {version!r}; known: {sorted(RULESETS)}") from e


def ruleset_for_date(d: date) -> RuleSet:
    """The rule set in force on ``d`` (latest ``effective_from`` <= d)."""
    eligible = [r for r in RULESETS.values() if r.effective_from <= d]
    if not eligible:
        earliest = min(RULESETS.values(), key=lambda r: r.effective_from)
        raise ValueError(
            f"no rule set effective on {d}; earliest is {earliest.version} "
            f"({earliest.effective_from}). Pass a rule set explicitly."
        )
    return max(eligible, key=lambda r: r.effective_from)
