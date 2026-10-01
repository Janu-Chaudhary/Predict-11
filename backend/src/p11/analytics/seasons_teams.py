"""Franchise naming: short codes and season-correct display names for the canonical teams.

The DB keeps one canonical row per franchise (renames and the Deccan Chargers -> Sunrisers
merge are folded together through ``team_alias``). Tables and match cards should still show
the name the franchise played under *that* season, so the era rules live here, keyed by the
canonical (current) name rather than by autoincrement id.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Era:
    name: str
    short_code: str
    from_year: int | None  # inclusive; None = open
    to_year: int | None  # inclusive; None = open


# canonical name -> eras, oldest first. The last era is the current identity.
_ERAS: dict[str, tuple[Era, ...]] = {
    "Chennai Super Kings": (Era("Chennai Super Kings", "CSK", None, None),),
    "Mumbai Indians": (Era("Mumbai Indians", "MI", None, None),),
    "Royal Challengers Bengaluru": (
        Era("Royal Challengers Bangalore", "RCB", None, 2023),
        Era("Royal Challengers Bengaluru", "RCB", 2024, None),
    ),
    "Kolkata Knight Riders": (Era("Kolkata Knight Riders", "KKR", None, None),),
    "Delhi Capitals": (
        Era("Delhi Daredevils", "DD", None, 2018),
        Era("Delhi Capitals", "DC", 2019, None),
    ),
    "Punjab Kings": (
        Era("Kings XI Punjab", "KXIP", None, 2020),
        Era("Punjab Kings", "PBKS", 2021, None),
    ),
    "Rajasthan Royals": (Era("Rajasthan Royals", "RR", None, None),),
    "Sunrisers Hyderabad": (
        Era("Deccan Chargers", "DCH", None, 2012),
        Era("Sunrisers Hyderabad", "SRH", 2013, None),
    ),
    "Gujarat Titans": (Era("Gujarat Titans", "GT", None, None),),
    "Lucknow Super Giants": (Era("Lucknow Super Giants", "LSG", None, None),),
    "Rising Pune Supergiant": (
        Era("Rising Pune Supergiants", "RPS", None, 2016),
        Era("Rising Pune Supergiant", "RPS", 2017, None),
    ),
    "Gujarat Lions": (Era("Gujarat Lions", "GL", None, None),),
    "Kochi Tuskers Kerala": (Era("Kochi Tuskers Kerala", "KTK", None, None),),
    "Pune Warriors": (Era("Pune Warriors", "PWI", None, None),),
}


def _fallback_code(name: str) -> str:
    words = [w for w in name.replace("-", " ").split() if w[:1].isalpha()]
    return "".join(w[0] for w in words).upper()[:4] or name[:3].upper()


def eras(canonical_name: str) -> tuple[Era, ...]:
    return _ERAS.get(
        canonical_name, (Era(canonical_name, _fallback_code(canonical_name), None, None),)
    )


def era_for(canonical_name: str, year: int | None) -> Era:
    """The identity the franchise used in ``year`` (current identity when year is None)."""
    all_eras = eras(canonical_name)
    if year is None:
        return all_eras[-1]
    for e in all_eras:
        if (e.from_year is None or year >= e.from_year) and (
            e.to_year is None or year <= e.to_year
        ):
            return e
    return all_eras[-1]


def short_code(canonical_name: str) -> str:
    """Current short code (e.g. "SRH" for the franchise that was once Deccan Chargers)."""
    return era_for(canonical_name, None).short_code


def all_codes(canonical_name: str) -> set[str]:
    return {e.short_code for e in eras(canonical_name)}
