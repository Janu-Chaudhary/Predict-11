"""Display-name rows and search match quality (pure, no DB)."""

from __future__ import annotations

from p11.analytics.players_identity import NameEntry, match_quality, normalize
from p11.registry.display_names import build_rows


def _e(name: str, primary: bool = True) -> NameEntry:
    n = normalize(name)
    return NameEntry("p", name, n, n.replace(" ", ""), primary)


def test_build_rows_one_display_name_per_player_in_source_order() -> None:
    rows = build_rows(
        {
            "a": {
                "bcci": ["Suryakumar Yadav"],
                "espn_api": ["Suryakumar Yadav", "Surya Kumar Yadav"],
            },
            "b": {"iplt20_2025": ["Virat Kohli"]},
        }
    )
    assert rows == [
        {"player_id": "a", "name": "Suryakumar Yadav", "source": "display"},
        {"player_id": "a", "name": "Surya Kumar Yadav", "source": "display_alt"},
        {"player_id": "b", "name": "Virat Kohli", "source": "display"},
    ]


def test_match_quality_tiers() -> None:
    q = lambda e, s: match_quality(e, normalize(s), normalize(s).split())  # noqa: E731
    assert q(_e("Rohit Sharma"), "rohit sharma") == 0  # exact
    assert q(_e("Rohit Sharma"), "rohit") == 2  # word prefix
    assert q(_e("Rohit Sharma"), "sha roh") == 2  # tokens in any order
    assert q(_e("Surya Kumar Yadav"), "suryakumar") == 2  # compact prefix
    assert q(_e("Sharma", primary=False), "sharma") == 3  # one-word alias is not "exact"
    assert q(_e("AB de Villiers"), "illie") == 4  # substring
    assert q(_e("S.A. Yadav"), "sa yadav") == 0  # dots ignored
    assert q(_e("Virat Kohli"), "bumrah") is None
