"""Source-agnostic input types for the fantasy scorer.

The shapes here mirror the normalized delivery format produced by the ingest spikes
(cricbuzz / espncricinfo / iplt20 / cricsheet), with a few optional fields that let a
richer source supply information the bare normalized shape cannot express
(run-out direct-hit flag, overthrow boundaries, mixed extras on one ball).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class ExtraType(StrEnum):
    WIDES = "wides"
    NOBALLS = "noballs"
    LEGBYES = "legbyes"
    BYES = "byes"
    PENALTY = "penalty"


class Role(StrEnum):
    """Dream11 player role. Duck and strike-rate rules depend on it."""

    WK = "WK"
    BAT = "BAT"
    AR = "AR"
    BOWL = "BOWL"


class LineupStatus(StrEnum):
    STARTING_XI = "starting_xi"
    """Named in the announced playing XI and started the match (+4 lineup points)."""

    SUBSTITUTE_PLAYED = "substitute_played"
    """Impact Player / concussion / X-factor / full-time replacement who came on (+4)."""

    SUBSTITUTE_UNUSED = "substitute_unused"
    """Announced substitute who never came on (0 points)."""

    WITHDRAWN = "withdrawn"
    """Announced in the XI but unable to start the match (0 points, contributions ignored)."""


# Dismissals credited to the bowler (Dream11 "Wicket (Excluding Run Out)").
BOWLER_WICKET_KINDS: frozenset[str] = frozenset(
    {"bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket"}
)
LBW_BOWLED_KINDS: frozenset[str] = frozenset({"bowled", "lbw"})
# Not a dismissal: the batter's innings is merely paused (no duck, no wicket).
NON_DISMISSAL_KINDS: frozenset[str] = frozenset({"retired hurt", "retired not out"})


@dataclass(frozen=True, slots=True)
class Delivery:
    """One ball (legal or not) of a match.

    ``over`` is 0-based (as in Cricsheet); ``ball`` is the sequence within the over and
    is only used for ordering/debugging. ``extras``/``extra_type`` follow the normalized
    shape (one extra type per ball). When a ball carries more than one kind of extra
    (e.g. no-ball + byes) a source may pass ``extras_detail`` (``{"noballs": 1,
    "byes": 4}``); it then overrides ``extras``/``extra_type`` for bowler accounting.

    Fielding:
      * ``fielders`` lists fielders credited on the dismissal in the order the source
        gives them (Cricsheet: thrower first, then the player at the stumps).
      * ``runout_direct``: True = direct hit (one fielder only touched the ball),
        False = not a direct hit. None = unknown -> inferred from ``len(fielders)``
        (1 fielder => direct hit).
    ``is_boundary``: None = infer (batter_runs of 4/6 is a boundary). Sources that know
    the runs were all-run or an overthrow (Cricsheet ``non_boundary``) pass False.
    """

    innings: int
    over: int
    ball: int
    batter: str
    bowler: str
    non_striker: str | None = None
    batter_runs: int = 0
    extras: int = 0
    extra_type: ExtraType | str | None = None
    super_over: bool = False
    wicket_kind: str | None = None
    player_out: str | None = None
    fielders: tuple[str, ...] = ()
    runout_direct: bool | None = None
    is_boundary: bool | None = None
    extras_detail: Mapping[str, int] | None = field(default=None, hash=False)

    def extra_components(self) -> dict[str, int]:
        if self.extras_detail is not None:
            return {str(k): int(v) for k, v in self.extras_detail.items() if v}
        if self.extra_type is None or self.extras == 0:
            # A no-ball/wide always carries >= 1 extra; tolerate sources that put the
            # type but forgot the run by still honouring the type below.
            return {str(self.extra_type): 0} if self.extra_type is not None else {}
        return {str(self.extra_type): self.extras}

    @property
    def is_wide(self) -> bool:
        return ExtraType.WIDES.value in self.extra_components()

    @property
    def is_noball(self) -> bool:
        return ExtraType.NOBALLS.value in self.extra_components()

    @property
    def is_legal(self) -> bool:
        """Counts towards the six balls of an over."""
        return not (self.is_wide or self.is_noball)

    @property
    def runs_conceded_by_bowler(self) -> int:
        """Batter runs + wides + no-ball extras. Byes, leg-byes and penalties are not
        charged to the bowler (Laws of Cricket 22/21, standard economy convention)."""
        comp = self.extra_components()
        return (
            self.batter_runs
            + comp.get(ExtraType.WIDES.value, 0)
            + comp.get(ExtraType.NOBALLS.value, 0)
        )

    @property
    def counts_as_ball_faced(self) -> bool:
        """Wides are not balls faced; no-balls are."""
        return not self.is_wide

    @property
    def is_four(self) -> bool:
        return self.batter_runs == 4 and self.is_boundary is not False

    @property
    def is_six(self) -> bool:
        return self.batter_runs == 6 and self.is_boundary is not False


@dataclass(frozen=True, slots=True)
class LineupEntry:
    player: str
    team: str
    role: Role
    status: LineupStatus = LineupStatus.STARTING_XI
