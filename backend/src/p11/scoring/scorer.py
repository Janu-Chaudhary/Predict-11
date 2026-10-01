"""Pure Dream11 fantasy-points scorer.

``score_match(deliveries, lineup, rules)`` -> ``MatchScore`` with, for every player in
the lineup, raw stats, an itemised breakdown and category totals:

  batting  = runs + boundary bonus + six bonus + duck
  bowling  = dot balls + wickets + LBW/bowled bonus + maidens
  fielding = catches + stumpings + run-outs (direct / indirect)
  lineup   = announced-XI or playing-substitute points
  bonuses  = threshold bonuses/penalties: run milestone, strike-rate band,
             wicket haul, economy band, 3-catch bonus

``total == batting + bowling + fielding + lineup + bonuses == sum(items.values())``.
Captain / vice-captain multipliers are applied separately (``fantasy_team_points``)
because they belong to a user's team, not to the player.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from types import MappingProxyType

from p11.scoring.rules import HaulMode, MilestoneMode, RuleSet, band_points
from p11.scoring.types import (
    BOWLER_WICKET_KINDS,
    LBW_BOWLED_KINDS,
    NON_DISMISSAL_KINDS,
    Delivery,
    LineupEntry,
    LineupStatus,
)

CATEGORY_OF: Mapping[str, str] = MappingProxyType(
    {
        "runs": "batting",
        "boundary_bonus": "batting",
        "six_bonus": "batting",
        "duck": "batting",
        "dot_balls": "bowling",
        "wickets": "bowling",
        "lbw_bowled_bonus": "bowling",
        "maidens": "bowling",
        "catches": "fielding",
        "stumpings": "fielding",
        "runout_direct": "fielding",
        "runout_indirect": "fielding",
        "lineup": "lineup",
        "run_milestone": "bonuses",
        "strike_rate": "bonuses",
        "wicket_haul": "bonuses",
        "economy": "bonuses",
        "catch_bonus": "bonuses",
    }
)
CATEGORIES: tuple[str, ...] = ("batting", "bowling", "fielding", "lineup", "bonuses")


@dataclass(slots=True)
class PlayerStats:
    # batting
    batted: bool = False
    runs: int = 0
    balls_faced: int = 0
    fours: int = 0
    sixes: int = 0
    dismissed: bool = False
    dismissal_kind: str | None = None
    # bowling
    legal_balls_bowled: int = 0
    runs_conceded: int = 0
    dot_balls: int = 0
    wickets: int = 0
    lbw_bowled: int = 0
    maidens: int = 0
    # fielding
    catches: int = 0
    stumpings: int = 0
    runouts_direct: int = 0
    runouts_indirect: int = 0

    @property
    def strike_rate(self) -> Fraction | None:
        return Fraction(100 * self.runs, self.balls_faced) if self.balls_faced else None

    @property
    def economy(self) -> Fraction | None:
        if not self.legal_balls_bowled:
            return None
        return Fraction(6 * self.runs_conceded, self.legal_balls_bowled)


@dataclass(frozen=True, slots=True)
class PlayerScore:
    player: str
    team: str
    role: str
    status: LineupStatus
    stats: PlayerStats
    items: Mapping[str, int]
    batting: int
    bowling: int
    fielding: int
    lineup: int
    bonuses: int
    total: int

    def multiplied(self, multiplier: float) -> float:
        return self.total * multiplier


@dataclass(frozen=True, slots=True)
class MatchScore:
    rules_version: str
    players: Mapping[str, PlayerScore]
    unscored_participants: frozenset[str] = field(default_factory=frozenset)
    """Names that appear in deliveries but are not scoring lineup members (e.g. ordinary
    substitute fielders). Their contributions earn nothing, per Dream11."""
    warnings: tuple[str, ...] = ()

    def __getitem__(self, player: str) -> PlayerScore:
        return self.players[player]


# ---------------------------------------------------------------- aggregation


def _participants(d: Delivery) -> set[str]:
    names = {d.batter, d.bowler, *d.fielders}
    if d.non_striker:
        names.add(d.non_striker)
    if d.player_out:
        names.add(d.player_out)
    return names


def _aggregate(deliveries: Iterable[Delivery], rules: RuleSet) -> dict[str, PlayerStats]:
    stats: dict[str, PlayerStats] = defaultdict(PlayerStats)
    # (innings, over) -> per-bowler legal balls / conceded, to detect maidens
    overs: dict[tuple[int, int], dict[str, list[int]]] = defaultdict(dict)

    for d in deliveries:
        if d.super_over and not rules.count_super_over:
            continue

        # ---- batting (striker)
        bat = stats[d.batter]
        bat.batted = True
        bat.runs += d.batter_runs
        if d.counts_as_ball_faced:
            bat.balls_faced += 1
        if d.is_four:
            bat.fours += 1
        elif d.is_six:
            bat.sixes += 1
        if d.non_striker:
            stats[d.non_striker].batted = True

        # ---- bowling
        bowl = stats[d.bowler]
        conceded = d.runs_conceded_by_bowler
        bowl.runs_conceded += conceded
        if d.is_legal:
            bowl.legal_balls_bowled += 1
            comp = d.extra_components()
            only_bye_like = all(k in ("byes", "legbyes") for k in comp)
            if d.batter_runs == 0 and (
                not comp or (only_bye_like and rules.dot_ball_counts_byes_legbyes)
            ):
                bowl.dot_balls += 1
        per_bowler = overs[(d.innings, d.over)].setdefault(d.bowler, [0, 0])
        per_bowler[0] += 1 if d.is_legal else 0
        per_bowler[1] += conceded

        # ---- dismissal
        kind = (d.wicket_kind or "").strip().lower() or None
        if kind and d.player_out:
            out = stats[d.player_out]
            out.batted = True
            if kind not in NON_DISMISSAL_KINDS:
                out.dismissed = True
                out.dismissal_kind = kind
            if kind in BOWLER_WICKET_KINDS:
                bowl.wickets += 1
                if kind in LBW_BOWLED_KINDS:
                    bowl.lbw_bowled += 1
            if kind == "caught":
                for f in d.fielders[:1]:
                    stats[f].catches += 1
            elif kind == "caught and bowled":
                if rules.caught_and_bowled_counts_as_catch:
                    bowl.catches += 1
            elif kind == "stumped":
                for f in d.fielders[:1]:
                    stats[f].stumpings += 1
            elif kind == "run out" and d.fielders:
                direct = d.runout_direct
                if direct is None:
                    direct = len(d.fielders) == 1
                if direct:
                    stats[d.fielders[0]].runouts_direct += 1
                else:
                    # "points will be awarded only to the last 2 fielders who touch the ball"
                    for f in dict.fromkeys(d.fielders[-rules.runout_indirect_max_fielders :]):
                        stats[f].runouts_indirect += 1

    # maidens: a complete over (6 legal balls) by a single bowler conceding 0
    for per_over in overs.values():
        if len(per_over) != 1:
            continue  # over shared between bowlers (injury) -> no maiden
        ((bowler, (legal, conceded)),) = per_over.items()
        if legal >= 6 and conceded == 0:
            stats[bowler].maidens += 1

    return dict(stats)


# ---------------------------------------------------------------- points


def _milestone_points(runs: int, rules: RuleSet) -> int:
    reached = [(t, p) for t, p in rules.run_milestones if runs >= t]
    if not reached:
        return 0
    if rules.milestone_mode is MilestoneMode.HIGHEST_ONLY:
        return max(reached)[1]
    # STACK_BELOW_CENTURY: a century replaces every lower milestone
    top_t, top_p = max(reached)
    if top_t >= rules.century_runs:
        return top_p
    return sum(p for _, p in reached)


def _haul_points(wickets: int, rules: RuleSet) -> int:
    reached = [(t, p) for t, p in rules.wicket_hauls if wickets >= t]
    if not reached:
        return 0
    if rules.haul_mode is HaulMode.HIGHEST_ONLY:
        return max(reached)[1]
    return sum(p for _, p in reached)


def _items(entry: LineupEntry, s: PlayerStats, rules: RuleSet) -> dict[str, int]:
    it: dict[str, int] = dict.fromkeys(CATEGORY_OF, 0)
    if entry.status in (LineupStatus.WITHDRAWN, LineupStatus.SUBSTITUTE_UNUSED):
        return it

    it["lineup"] = (
        rules.announced_lineup
        if entry.status is LineupStatus.STARTING_XI
        else rules.substitute_played
    )

    # batting
    it["runs"] = s.runs * rules.run
    it["boundary_bonus"] = s.fours * rules.boundary_bonus
    it["six_bonus"] = s.sixes * rules.six_bonus
    it["run_milestone"] = _milestone_points(s.runs, rules)
    if s.dismissed and s.runs == 0 and entry.role in rules.duck_roles:
        it["duck"] = rules.duck
    if (
        entry.role not in rules.strike_rate_exempt_roles
        and s.balls_faced >= rules.strike_rate_min_balls
        and s.strike_rate is not None
    ):
        it["strike_rate"] = band_points(rules.strike_rate_bands, s.strike_rate)

    # bowling
    it["dot_balls"] = s.dot_balls * rules.dot_ball
    it["wickets"] = s.wickets * rules.wicket
    it["lbw_bowled_bonus"] = s.lbw_bowled * rules.lbw_bowled_bonus
    it["wicket_haul"] = _haul_points(s.wickets, rules)
    it["maidens"] = s.maidens * rules.maiden
    if s.legal_balls_bowled >= rules.economy_min_balls and s.economy is not None:
        it["economy"] = band_points(rules.economy_bands, s.economy)

    # fielding
    it["catches"] = s.catches * rules.catch
    if s.catches >= rules.catch_bonus_threshold:
        it["catch_bonus"] = rules.catch_bonus
    it["stumpings"] = s.stumpings * rules.stumping
    it["runout_direct"] = s.runouts_direct * rules.runout_direct
    it["runout_indirect"] = s.runouts_indirect * rules.runout_indirect
    return it


def score_match(
    deliveries: Iterable[Delivery],
    lineup: Iterable[LineupEntry],
    rules: RuleSet,
) -> MatchScore:
    """Score every lineup member of one match under ``rules``.

    Only lineup members score. Names that appear in the deliveries but are not in the
    lineup (ordinary substitute fielders) are reported in ``unscored_participants``.
    A ``SUBSTITUTE_UNUSED`` entry that does appear in the deliveries is promoted to
    ``SUBSTITUTE_PLAYED`` (with a warning) since the data shows they took part.
    """
    deliveries = list(deliveries)
    entries: dict[str, LineupEntry] = {}
    for e in lineup:
        if e.player in entries:
            raise ValueError(f"duplicate lineup entry for {e.player!r}")
        entries[e.player] = e

    stats = _aggregate(deliveries, rules)
    seen: set[str] = set()
    for d in deliveries:
        if d.super_over and not rules.count_super_over:
            continue
        seen |= _participants(d)

    warnings: list[str] = []
    players: dict[str, PlayerScore] = {}
    for name, entry in entries.items():
        if entry.status is LineupStatus.SUBSTITUTE_UNUSED and name in seen:
            warnings.append(f"{name}: marked unused substitute but appears in deliveries")
            entry = LineupEntry(entry.player, entry.team, entry.role,
                                LineupStatus.SUBSTITUTE_PLAYED)
        s = stats.get(name, PlayerStats())
        it = _items(entry, s, rules)
        cats = dict.fromkeys(CATEGORIES, 0)
        for k, v in it.items():
            cats[CATEGORY_OF[k]] += v
        players[name] = PlayerScore(
            player=name,
            team=entry.team,
            role=str(entry.role),
            status=entry.status,
            stats=s,
            items=MappingProxyType(it),
            batting=cats["batting"],
            bowling=cats["bowling"],
            fielding=cats["fielding"],
            lineup=cats["lineup"],
            bonuses=cats["bonuses"],
            total=sum(cats.values()),
        )

    return MatchScore(
        rules_version=rules.version,
        players=MappingProxyType(players),
        unscored_participants=frozenset(seen - entries.keys()),
        warnings=tuple(warnings),
    )


def fantasy_team_points(
    match: MatchScore,
    picks: Iterable[str],
    captain: str,
    vice_captain: str,
    rules: RuleSet,
) -> float:
    """Total for a user's fantasy XI: captain x2, vice-captain x1.5 (per ``rules``)."""
    picks = list(picks)
    if captain == vice_captain:
        raise ValueError("captain and vice-captain must differ")
    if captain not in picks or vice_captain not in picks:
        raise ValueError("captain and vice-captain must be among the picks")
    total = 0.0
    for p in picks:
        mult = (
            rules.captain_multiplier
            if p == captain
            else rules.vice_captain_multiplier
            if p == vice_captain
            else 1.0
        )
        ps = match.players.get(p)
        total += ps.multiplied(mult) if ps else 0.0
    return total
