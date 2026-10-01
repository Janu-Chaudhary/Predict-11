"""Player attributes: Dream11 playing role, batting hand, bowling style.

Pure normalisers (any source's wording -> canonical values), the history-based role fallback,
and the source priorities used by the ``player_attribute_resolved`` view. Source loaders live
in ``p11.ingest.player_attributes``.

Canonical values
- playing_role: WK | BAT | AR | BOWL (``p11.scoring.Role``)
- batting_hand: R | L
- bowling_type (pace split by *speed band*, spin by *style*):
    right-arm fast    = fast, fast-medium            (RF, RFM)
    right-arm medium  = medium-fast, medium, slow-medium (RMF, RM, RSM)
    left-arm fast     = LF, LFM;  left-arm medium = LMF, LM
    off-spin          = right-arm off-break (also "left-arm offbreak" is not a thing: see below)
    leg-spin          = right-arm leg-break / googly
    left-arm orthodox = slow left-arm orthodox (SLA)
    left-arm wrist    = left-arm wrist-spin / chinaman (SLC)
  Players with several styles ("right-arm offbreak, legbreak") are typed by the first listed
  (sources list the primary style first).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

ROLES = ("WK", "BAT", "AR", "BOWL")
BOWLING_TYPES = (
    "right-arm fast",
    "right-arm medium",
    "off-spin",
    "leg-spin",
    "left-arm fast",
    "left-arm medium",
    "left-arm orthodox",
    "left-arm wrist",
)

# Per-field source priority (lowest index wins). Official IPL squads decide the Dream11 role;
# ESPNcricinfo has the most precise style wording. Keep in sync with the migration's view.
ROLE_PRIORITY = ("bcci", "iplt20_2025", "cricinfo", "espn_api", "cricbuzz", "derived")
STYLE_PRIORITY = ("cricinfo", "espn_api", "bcci", "cricbuzz", "iplt20_2025", "derived")

# Short codes (BCCI ``bowling_desc``, ESPN ``bowlingStyles``) -> long wording.
_CODES = {
    "rf": "right-arm fast",
    "rfm": "right-arm fast-medium",
    "rmf": "right-arm medium-fast",
    "rm": "right-arm medium",
    "rsm": "right-arm slow-medium",
    "ob": "right-arm offbreak",
    "rob": "right-arm offbreak",
    "lb": "legbreak",
    "lbg": "legbreak googly",
    "rlb": "legbreak",
    "sla": "slow left-arm orthodox",
    "lo": "slow left-arm orthodox",
    "slc": "left-arm wrist-spin",
    "slw": "left-arm wrist-spin",
    "lws": "left-arm wrist-spin",
    "lc": "left-arm wrist-spin",
    "lf": "left-arm fast",
    "lfm": "left-arm fast-medium",
    "lmf": "left-arm medium-fast",
    "lm": "left-arm medium",
    "lsm": "left-arm slow-medium",
}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("_", " ").strip().casefold())


def normalize_bowling_type(raw: str | Iterable[str] | None) -> str | None:
    """Map any source's bowling-style text (or list of styles, primary first) to one of
    ``BOWLING_TYPES``; None when unknown/empty."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        for r in raw:
            if (t := normalize_bowling_type(r)) is not None:
                return t
        return None
    s = _clean(raw)
    if not s:
        return None
    s = s.split(",")[0].strip()
    s = _CODES.get(s, s)
    s = s.replace("off-break", "offbreak").replace("off break", "offbreak")
    s = s.replace("leg-break", "legbreak").replace("leg break", "legbreak")
    left = "left-arm" in s or "left arm" in s or s.startswith("left")
    if "wrist" in s or "chinaman" in s:
        return "left-arm wrist" if left else "leg-spin"
    if "orthodox" in s or s in ("slow left-arm", "left-arm spin", "left-arm slow"):
        return "left-arm orthodox"
    if "legbreak" in s or "leg spin" in s or "leg-spin" in s or "googly" in s:
        return "left-arm wrist" if left else "leg-spin"
    if "offbreak" in s or "off spin" in s or "off-spin" in s:
        # A left-armer "offbreak" is finger spin away from the right-hander = orthodox.
        return "left-arm orthodox" if left else "off-spin"
    i_fast, i_med = s.find("fast"), s.find("medium")
    if i_fast < 0 and i_med < 0:
        return None
    # the first speed word is the band: fast-medium -> fast, medium-fast -> medium
    fast = i_fast >= 0 and (i_med < 0 or i_fast < i_med)
    if left:
        return "left-arm fast" if fast else "left-arm medium"
    return "right-arm fast" if fast else "right-arm medium"


def normalize_batting_hand(raw: str | Iterable[str] | None) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        for r in raw:
            if (h := normalize_batting_hand(r)) is not None:
                return h
        return None
    s = _clean(raw)
    if s in ("rhb", "r", "right", "right-hand bat", "right hand bat", "right-handed"):
        return "R"
    if s in ("lhb", "l", "left", "left-hand bat", "left hand bat", "left-handed"):
        return "L"
    if s.startswith("right"):
        return "R"
    if s.startswith("left"):
        return "L"
    return None


def normalize_role(raw: str | Iterable[str] | None, *, keeper: bool = False) -> str | None:
    """Source role wording -> WK/BAT/AR/BOWL. ``keeper`` (an explicit WK flag) wins."""
    if keeper:
        return "WK"
    if raw is None:
        return None
    if not isinstance(raw, str):
        for r in raw:
            if (x := normalize_role(r)) is not None:
                return x
        return None
    s = _clean(raw).replace("-", " ")
    if not s or s == "undefined":
        return None
    if "keeper" in s or s.startswith("wk"):
        return "WK"
    if "allrounder" in s or "all rounder" in s or "all round" in s:
        return "AR"
    if "bowl" in s:
        return "BOWL"
    if "bat" in s:
        return "BAT"
    return None


# ------------------------------------------------------------------ history-based fallback


@dataclass(frozen=True, slots=True)
class CareerLine:
    """IPL career aggregates used to derive a role when no source has one."""

    matches: int
    balls_faced: int
    legal_balls_bowled: int
    stumpings: int = 0


# Thresholds chosen on players that have a scraped role (see report in
# p11.ingest.player_attributes.derived_accuracy): a frontline bowler sends down >= 12 legal
# balls a match on average (2 overs), a genuine all-rounder also faces >= 8 balls a match.
BOWLER_BALLS_PER_MATCH = 12.0
AR_FACED_PER_MATCH = 8.0
PART_TIME_BALLS_PER_MATCH = 6.0
AR_FACED_PART_TIME = 12.0


def derive_role(c: CareerLine) -> str | None:
    """Role from history: any stumping -> WK; else by bowling share. None without matches."""
    if c.matches <= 0:
        return None
    if c.stumpings > 0:
        return "WK"
    bowled = c.legal_balls_bowled / c.matches
    faced = c.balls_faced / c.matches
    if bowled >= BOWLER_BALLS_PER_MATCH:
        return "AR" if faced >= AR_FACED_PER_MATCH else "BOWL"
    if bowled >= PART_TIME_BALLS_PER_MATCH:
        return "AR" if faced >= AR_FACED_PART_TIME else "BOWL"
    if bowled > 0 and faced < 2.0 and c.legal_balls_bowled >= 6:
        return "BOWL"  # bowls a little, barely bats: a bowler who was under-used
    return "BAT"


def resolve(rows: Iterable[dict], field: str) -> tuple[str | None, str | None]:
    """Python mirror of the resolved view for one field: (value, source)."""
    prio = ROLE_PRIORITY if field == "playing_role" else STYLE_PRIORITY
    best: tuple[int, str, str] | None = None
    for r in rows:
        v = r.get(field)
        if v is None:
            continue
        rank = prio.index(r["source"]) if r["source"] in prio else 99
        if best is None or rank < best[0]:
            best = (rank, v, r["source"])
    return (best[1], best[2]) if best else (None, None)
