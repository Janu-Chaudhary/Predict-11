"""Dream11 fantasy-points scoring (pure, versioned). Rules and sources: RULES.md."""

from p11.scoring.rules import (
    DEFAULT_RULESET,
    RULESETS,
    T20_2024,
    T20_2025,
    T20_2026,
    Band,
    HaulMode,
    MilestoneMode,
    RuleSet,
    get_ruleset,
    ruleset_for_date,
)
from p11.scoring.scorer import (
    CATEGORIES,
    MatchScore,
    PlayerScore,
    PlayerStats,
    fantasy_team_points,
    score_match,
)
from p11.scoring.types import Delivery, ExtraType, LineupEntry, LineupStatus, Role

__all__ = [
    "CATEGORIES",
    "DEFAULT_RULESET",
    "RULESETS",
    "T20_2024",
    "T20_2025",
    "T20_2026",
    "Band",
    "Delivery",
    "ExtraType",
    "HaulMode",
    "LineupEntry",
    "LineupStatus",
    "MatchScore",
    "MilestoneMode",
    "PlayerScore",
    "PlayerStats",
    "Role",
    "RuleSet",
    "fantasy_team_points",
    "get_ruleset",
    "ruleset_for_date",
    "score_match",
]
