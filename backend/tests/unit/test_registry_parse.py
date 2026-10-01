"""Registry CSV parsing, team/venue canonicalisation, credits CSV quirks."""

from __future__ import annotations

from decimal import Decimal

from p11.registry.canonical import canonical_team_name, canonical_venue_name
from p11.registry.credits import initial_surname_match, read_team_csv, team_name_from_file
from p11.registry.people import parse_names, parse_people
from tests.fixtures import CRICSHEET


def test_people_source_keys():
    players, sids = parse_people(CRICSHEET / "people.csv")
    assert len(players) == 82
    kohli = [s for s in sids if s["player_id"] == "ba607b88"]
    assert {"source": "cricinfo", "source_key": "253802", "player_id": "ba607b88"} in kohli
    assert {s["source"] for s in sids} >= {"cricinfo", "pulse", "bcci"}
    assert not any(s["source"].endswith(("_2", "_3")) for s in sids)


def test_names_aliases():
    aliases = parse_names(CRICSHEET / "names.csv")
    assert {"player_id": "ba607b88", "name": "Virat Kohli", "source": "cricsheet_names"} in aliases


def test_team_renames():
    assert canonical_team_name("Royal Challengers Bangalore") == "Royal Challengers Bengaluru"
    assert canonical_team_name("Delhi Daredevils") == "Delhi Capitals"
    assert canonical_team_name("Kings XI Punjab") == "Punjab Kings"
    assert canonical_team_name("Deccan Chargers") == "Sunrisers Hyderabad"  # owner-approved merge


def test_venue_variants_collapse():
    assert canonical_venue_name("Wankhede Stadium, Mumbai") == "Wankhede Stadium"
    assert canonical_venue_name("Wankhede Stadium") == "Wankhede Stadium"
    assert canonical_venue_name("MA Chidambaram Stadium, Chepauk, Chennai") == (
        "MA Chidambaram Stadium"
    )
    assert canonical_venue_name("M.Chinnaswamy Stadium") == "M Chinnaswamy Stadium"
    assert canonical_venue_name("Feroz Shah Kotla") == "Arun Jaitley Stadium"


def test_credit_csv_quirks(tmp_path):
    p = tmp_path / "royal-challengers-bengaluru_squad.csv"
    p.write_bytes(
        "﻿Name,Role,Foreign Player,Credit Points,Full Name\n"
        "Virat Kohli,Batter,False,9, V Kohli\n"
        "Some Bowler,Bowler,False,6.5K Bowler\n"
        "No Credit,Bowler,False,,N Credit\n".encode()
    )
    rows = read_team_csv(p)
    assert team_name_from_file(p) == "Royal Challengers Bengaluru"
    assert (rows[0].full_name, rows[0].credits) == ("V Kohli", Decimal("9"))
    assert (rows[1].full_name, rows[1].credits) == ("K Bowler", Decimal("6.5"))
    assert rows[2].credits is None


def test_initial_surname_match():
    assert initial_surname_match("Manav Suthar", "MJ Suthar")
    assert initial_surname_match("Mohammad Shami", "Mohammed Shami")
    assert not initial_surname_match("Manvanth Kumar", "Mukesh Kumar")
    assert not initial_surname_match("Manav Suthar", "MJ Sutar")
