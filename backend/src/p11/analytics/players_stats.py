"""Pure cricket stat definitions (no DB). Single source of truth for player / matchup maths.

Definitions (T20, Cricsheet ball-by-ball):
- A ball *faced* by the batter is any delivery that is not a wide (no-balls count as faced).
- Strike rate = runs / balls faced * 100. Batting average = runs / dismissals, where retired hurt
  (and retired not out) is not a dismissal; a non-striker run out is the non-striker's dismissal.
- A *legal* ball (for the bowler) is neither a wide nor a no-ball.
- Runs conceded by the bowler = batter runs + wides + no-balls; byes, leg-byes and penalties are
  not charged to the bowler.
- Bowler wickets exclude run outs, retirements and obstructing the field.
- Economy = runs conceded / legal balls * 6. A dot ball is a legal ball with 0 runs charged to
  the bowler (on a legal ball that is simply ``batter_runs == 0``).
- Phases by 0-indexed over: powerplay 0-5, middle 6-14, death 15-19.
Super-over balls are never passed in (callers filter them).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass, field

NOT_DISMISSALS = frozenset({"retired hurt", "retired not out"})
NOT_BOWLER_WICKETS = frozenset(
    {"run out", "retired hurt", "retired out", "retired not out", "obstructing the field"}
)
PHASES: tuple[str, ...] = ("powerplay", "middle", "death")


def phase_of(over: int) -> str:
    """0-indexed over -> phase name."""
    if over <= 5:
        return "powerplay"
    if over <= 14:
        return "middle"
    return "death"


@dataclass(slots=True)
class Ball:
    match_id: int
    innings: int
    over: int
    batter: str
    bowler: str
    non_striker: str = ""
    batter_runs: int = 0
    wides: int = 0
    noballs: int = 0
    byes: int = 0
    legbyes: int = 0
    penalty: int = 0
    non_boundary: bool = False
    wicket_kind: str | None = None
    player_out: str | None = None
    fielders: tuple[str, ...] = ()

    @property
    def faced(self) -> bool:
        return self.wides == 0

    @property
    def legal(self) -> bool:
        return self.wides == 0 and self.noballs == 0

    @property
    def bowler_runs(self) -> int:
        return self.batter_runs + self.wides + self.noballs

    @property
    def total_runs(self) -> int:
        return (
            self.batter_runs + self.wides + self.noballs + self.byes + self.legbyes + self.penalty
        )

    @property
    def four(self) -> bool:
        return self.batter_runs == 4 and not self.non_boundary

    @property
    def six(self) -> bool:
        return self.batter_runs == 6 and not self.non_boundary

    @property
    def bowler_wicket(self) -> bool:
        return (
            self.player_out is not None
            and self.wicket_kind is not None
            and self.wicket_kind not in NOT_BOWLER_WICKETS
        )

    @property
    def dismissal(self) -> bool:
        """Someone (``player_out``) was dismissed on this ball (retired hurt excluded)."""
        return self.player_out is not None and (self.wicket_kind or "") not in NOT_DISMISSALS

    @property
    def dot(self) -> bool:
        return self.legal and self.batter_runs == 0


# --------------------------------------------------------------------------- cards
@dataclass(slots=True)
class BattingCard:
    match_id: int
    innings: int
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    dots: int = 0
    out: bool = False
    how_out: str | None = None

    @property
    def duck(self) -> bool:
        return self.out and self.runs == 0


@dataclass(slots=True)
class BowlingCard:
    match_id: int
    innings: int
    balls: int = 0  # legal
    runs: int = 0
    wickets: int = 0
    dots: int = 0
    maidens: int = 0
    wides: int = 0
    noballs: int = 0
    fours: int = 0
    sixes: int = 0

    @property
    def figures(self) -> str:
        return f"{self.wickets}/{self.runs}"


def batting_cards(balls: Iterable[Ball], player: str) -> list[BattingCard]:
    """One card per (match, innings) in which ``player`` batted (striker, non-striker or out)."""
    cards: dict[tuple[int, int], BattingCard] = {}

    def card(b: Ball) -> BattingCard:
        key = (b.match_id, b.innings)
        c = cards.get(key)
        if c is None:
            c = cards[key] = BattingCard(b.match_id, b.innings)
        return c

    for b in balls:
        if player not in (b.batter, b.non_striker, b.player_out):
            continue
        c = card(b)
        if b.batter == player:
            c.runs += b.batter_runs
            if b.faced:
                c.balls += 1
                if b.batter_runs == 0 and b.noballs == 0:
                    c.dots += 1
            c.fours += b.four
            c.sixes += b.six
        if b.player_out == player and b.dismissal:
            c.out = True
            c.how_out = b.wicket_kind
    return list(cards.values())  # first-seen order (callers pass chronological balls)


def bowling_cards(balls: Iterable[Ball], player: str) -> list[BowlingCard]:
    cards: dict[tuple[int, int], BowlingCard] = {}
    overs: dict[tuple[int, int, int], list[int]] = defaultdict(lambda: [0, 0])  # legal, runs
    for b in balls:
        if b.bowler != player:
            continue
        key = (b.match_id, b.innings)
        c = cards.get(key)
        if c is None:
            c = cards[key] = BowlingCard(b.match_id, b.innings)
        c.runs += b.bowler_runs
        c.wides += b.wides > 0
        c.noballs += b.noballs > 0
        c.fours += b.four
        c.sixes += b.six
        if b.legal:
            c.balls += 1
            c.dots += b.dot
        if b.bowler_wicket:
            c.wickets += 1
        o = overs[(b.match_id, b.innings, b.over)]
        o[0] += b.legal
        o[1] += b.bowler_runs
    for (m, i, _), (legal, runs) in overs.items():
        if legal >= 6 and runs == 0:
            cards[(m, i)].maidens += 1
    return list(cards.values())  # first-seen order (callers pass chronological balls)


@dataclass(slots=True)
class Fielding:
    catches: int = 0
    stumpings: int = 0
    run_outs: int = 0


def fielding(balls: Iterable[Ball], player: str) -> Fielding:
    """Caught (incl. caught & bowled), stumped, and run-out involvements (direct or assist)."""
    f = Fielding()
    for b in balls:
        if b.player_out is None:
            continue
        k = b.wicket_kind
        if (
            k == "caught"
            and player in b.fielders
            or k == "caught and bowled"
            and (b.bowler == player)
        ):
            f.catches += 1
        elif k == "stumped" and player in b.fielders:
            f.stumpings += 1
        elif k == "run out" and player in b.fielders:
            f.run_outs += 1
    return f


# --------------------------------------------------------------------------- lines
def _rate(num: float, den: float, scale: float = 1.0) -> float | None:
    return round(num / den * scale, 2) if den else None


def overs_str(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}" if balls % 6 else str(balls // 6)


@dataclass(slots=True)
class BattingLine:
    innings: int = 0
    not_outs: int = 0
    runs: int = 0
    balls: int = 0
    average: float | None = None
    strike_rate: float | None = None
    fifties: int = 0
    hundreds: int = 0
    thirties: int = 0
    ducks: int = 0
    fours: int = 0
    sixes: int = 0
    dots: int = 0
    highest: int | None = None
    highest_not_out: bool = False

    @property
    def highest_str(self) -> str | None:
        if self.highest is None:
            return None
        return f"{self.highest}{'*' if self.highest_not_out else ''}"


def batting_line(cards: Sequence[BattingCard]) -> BattingLine:
    ln = BattingLine()
    best: tuple[int, bool] | None = None
    for c in cards:
        ln.innings += 1
        ln.not_outs += not c.out
        ln.runs += c.runs
        ln.balls += c.balls
        ln.fours += c.fours
        ln.sixes += c.sixes
        ln.dots += c.dots
        ln.hundreds += c.runs >= 100
        ln.fifties += 50 <= c.runs < 100
        ln.thirties += c.runs >= 30
        ln.ducks += c.duck
        # higher score wins; for equal scores a not-out ranks above
        cand = (c.runs, not c.out)
        if best is None or cand > best:
            best = cand
    dismissals = ln.innings - ln.not_outs
    ln.average = _rate(ln.runs, dismissals)
    ln.strike_rate = _rate(ln.runs, ln.balls, 100)
    if best is not None:
        ln.highest, ln.highest_not_out = best
    return ln


@dataclass(slots=True)
class BowlingLine:
    innings: int = 0
    balls: int = 0
    runs: int = 0
    wickets: int = 0
    maidens: int = 0
    dots: int = 0
    fours: int = 0
    sixes: int = 0
    economy: float | None = None
    average: float | None = None
    strike_rate: float | None = None
    dot_pct: float | None = None
    three_plus: int = 0
    four_plus: int = 0
    five_plus: int = 0
    best: str | None = None

    @property
    def overs(self) -> str:
        return overs_str(self.balls)


def best_figures(cards: Iterable[BowlingCard]) -> BowlingCard | None:
    best: BowlingCard | None = None
    for c in cards:
        if best is None or (c.wickets, -c.runs) > (best.wickets, -best.runs):
            best = c
    return best


def bowling_line(cards: Sequence[BowlingCard]) -> BowlingLine:
    ln = BowlingLine()
    for c in cards:
        ln.innings += 1
        ln.balls += c.balls
        ln.runs += c.runs
        ln.wickets += c.wickets
        ln.maidens += c.maidens
        ln.dots += c.dots
        ln.fours += c.fours
        ln.sixes += c.sixes
        ln.three_plus += c.wickets >= 3
        ln.four_plus += c.wickets >= 4
        ln.five_plus += c.wickets >= 5
    ln.economy = _rate(ln.runs, ln.balls, 6)
    ln.average = _rate(ln.runs, ln.wickets)
    ln.strike_rate = _rate(ln.balls, ln.wickets)
    ln.dot_pct = _rate(ln.dots, ln.balls, 100)
    b = best_figures(cards)
    ln.best = b.figures if b else None
    return ln


# --------------------------------------------------------------------------- phases
@dataclass(slots=True)
class PhaseBat:
    balls: int = 0
    runs: int = 0
    outs: int = 0
    fours: int = 0
    sixes: int = 0

    @property
    def strike_rate(self) -> float | None:
        return _rate(self.runs, self.balls, 100)


@dataclass(slots=True)
class PhaseBowl:
    balls: int = 0
    runs: int = 0
    wickets: int = 0
    dots: int = 0

    @property
    def economy(self) -> float | None:
        return _rate(self.runs, self.balls, 6)


def batting_phases(balls: Iterable[Ball], player: str) -> dict[str, PhaseBat]:
    out = {p: PhaseBat() for p in PHASES}
    for b in balls:
        ph = out[phase_of(b.over)]
        if b.batter == player:
            ph.runs += b.batter_runs
            ph.balls += b.faced
            ph.fours += b.four
            ph.sixes += b.six
        if b.player_out == player and b.dismissal:
            ph.outs += 1
    return out


def bowling_phases(balls: Iterable[Ball], player: str) -> dict[str, PhaseBowl]:
    out = {p: PhaseBowl() for p in PHASES}
    for b in balls:
        if b.bowler != player:
            continue
        ph = out[phase_of(b.over)]
        ph.runs += b.bowler_runs
        ph.balls += b.legal
        ph.dots += b.dot
        ph.wickets += b.bowler_wicket
    return out


# --------------------------------------------------------------------------- head to head
@dataclass(slots=True)
class H2H:
    balls: int = 0
    runs: int = 0
    dismissals: int = 0
    dots: int = 0
    fours: int = 0
    sixes: int = 0
    how_out: dict[str, int] = field(default_factory=dict)
    matches: set[int] = field(default_factory=set)
    innings: set[tuple[int, int]] = field(default_factory=set)

    @property
    def strike_rate(self) -> float | None:
        return _rate(self.runs, self.balls, 100)

    @property
    def average(self) -> float | None:
        return _rate(self.runs, self.dismissals)

    @property
    def dot_pct(self) -> float | None:
        return _rate(self.dots, self.balls, 100)

    @property
    def boundary_pct(self) -> float | None:
        return _rate(self.fours + self.sixes, self.balls, 100)

    def add(self, b: Ball) -> None:
        """Add one batter-v-bowler ball. Only bowler-credited dismissals of the striker count."""
        self.matches.add(b.match_id)
        self.innings.add((b.match_id, b.innings))
        self.runs += b.batter_runs
        if b.faced:
            self.balls += 1
        self.dots += b.dot
        self.fours += b.four
        self.sixes += b.six
        if b.bowler_wicket and b.player_out == b.batter:
            self.dismissals += 1
            k = b.wicket_kind or "unknown"
            self.how_out[k] = self.how_out.get(k, 0) + 1


def h2h(balls: Iterable[Ball]) -> H2H:
    agg = H2H()
    for b in balls:
        agg.add(b)
    return agg


def confidence(balls: int) -> str:
    """Sample-size badge: median batter-bowler pair has only ~5 balls."""
    if balls >= 30:
        return "high"
    if balls >= 12:
        return "medium"
    return "low"


# --------------------------------------------------------------------------- streaks
@dataclass(slots=True)
class Streak:
    current: int = 0
    longest: int = 0
    longest_start: int | None = None  # index into the sequence
    longest_end: int | None = None


def streak[T](seq: Sequence[T], ok: Callable[[T], bool]) -> Streak:
    """Current (ending at the last element) and longest run of consecutive ``ok`` items."""
    s = Streak()
    run, start = 0, 0
    for i, x in enumerate(seq):
        if ok(x):
            if run == 0:
                start = i
            run += 1
            if run > s.longest:
                s.longest, s.longest_start, s.longest_end = run, start, i
        else:
            run = 0
    s.current = run
    return s


# --------------------------------------------------------------------------- milestones
def next_milestone(value: int, step: int) -> int:
    """Smallest positive multiple of ``step`` strictly above ``value``."""
    return (value // step + 1) * step


def group_by[T, K: Hashable](items: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    out: dict[K, list[T]] = defaultdict(list)
    for x in items:
        out[key(x)].append(x)
    return dict(out)
