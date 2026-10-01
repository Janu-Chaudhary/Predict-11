"""Registry + Cricsheet backfill + credits + lake against a real Postgres (p11_test)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from sqlalchemy import Engine, text

from p11.ingest.backfill import backfill_zip
from p11.ingest.lake import export_lake
from p11.registry.credits import credits_for_season, load_credits
from p11.registry.people import load_registry
from tests.fixtures import ALL_MATCHES, CRICSHEET, FINAL, SUPER_OVER, cricsheet_json

pytestmark = pytest.mark.integration


def make_zip(path: Path, payloads: dict[int, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        for mid, data in payloads.items():
            z.writestr(f"{mid}.json", data)
    return path


def load_people(db: Engine):
    with db.begin() as c:
        return load_registry(c, CRICSHEET / "people.csv", CRICSHEET / "names.csv")


def scalar(db: Engine, sql: str, **kw):
    with db.connect() as c:
        return c.execute(text(sql), kw).scalar_one()


def test_registry_load_is_idempotent(db):
    first = load_people(db)
    assert first.by_table["player"].inserted == 82
    assert first.by_table["player_source_id"].inserted > 82
    assert load_people(db).total == 0
    assert (
        scalar(
            db,
            "SELECT player_id FROM player_source_id "
            "WHERE source = 'cricinfo' AND source_key = '253802'",
        )
        == "ba607b88"
    )


def test_backfill_twice_yields_zero_changes(db, tmp_path):
    load_people(db)
    z = make_zip(tmp_path / "ipl_json.zip", {m: cricsheet_json(m) for m in ALL_MATCHES})
    arch = tmp_path / "archive"

    r1 = backfill_zip(db, z, arch)
    assert (r1.loaded, len(r1.quarantined), r1.errors) == (4, 0, {})
    n_balls = scalar(db, "SELECT count(*) FROM delivery")
    assert n_balls == r1.changes.by_table["delivery"].inserted > 0
    assert scalar(db, "SELECT count(*) FROM match WHERE data_status = 'single_source'") == 4
    assert len(list((arch / "cricsheet").glob("*.json.gz"))) == 4

    r2 = backfill_zip(db, z, arch)  # unchanged sha256 -> skipped
    assert r2.skipped_unchanged == 4 and r2.changes.total == 0

    r3 = backfill_zip(db, z, arch, force=True)  # full re-parse + upsert -> still no diff
    assert r3.skipped_unchanged == 0 and r3.changes.total == 0, r3.changes.as_dict()

    # super-over balls stored as innings 3/4; teams canonicalised; registry ids only
    assert (
        scalar(
            db,
            "SELECT count(DISTINCT innings) FROM delivery WHERE match_id = :m AND super_over",
            m=SUPER_OVER,
        )
        == 2
    )
    assert (
        scalar(
            db,
            "SELECT count(*) FROM delivery d LEFT JOIN player p ON p.id = d.batter_id "
            "WHERE p.id IS NULL",
        )
        == 0
    )
    assert scalar(db, "SELECT count(*) FROM delivery_resolved") == n_balls


def test_corrupted_payload_is_quarantined_not_dropped(db, tmp_path):
    load_people(db)
    d = json.loads(cricsheet_json(FINAL))
    d["innings"][0]["overs"][3]["deliveries"][0]["runs"]["batter"] += 4  # breaks run sum
    d["innings"][1]["target"]["runs"] += 1  # breaks target == total + 1
    bad = make_zip(tmp_path / "bad.zip", {FINAL: json.dumps(d).encode()})

    rep = backfill_zip(db, bad, tmp_path / "a")
    assert set(rep.quarantined) == {FINAL}
    checks = {i["check"] for i in rep.quarantined[FINAL]}
    assert {"ball_runs", "totals"} <= checks
    assert scalar(db, "SELECT data_status FROM match WHERE id = :m", m=FINAL) == "quarantined"
    assert scalar(db, "SELECT status FROM match_source WHERE match_id = :m", m=FINAL) == (
        "quarantined"
    )
    assert scalar(db, "SELECT parse_status FROM raw_payload") == "quarantined"
    assert scalar(db, "SELECT count(*) FROM delivery WHERE match_id = :m", m=FINAL) > 0

    # the corrected payload replaces it and the match is clean again
    good = make_zip(tmp_path / "good.zip", {FINAL: cricsheet_json(FINAL)})
    rep2 = backfill_zip(db, good, tmp_path / "a")
    assert rep2.loaded == 1 and not rep2.quarantined
    assert scalar(db, "SELECT data_status FROM match WHERE id = :m", m=FINAL) == "single_source"
    assert scalar(db, "SELECT dq_issues IS NULL FROM match_source WHERE match_id = :m", m=FINAL)


def test_unknown_player_quarantines_without_child_rows(db, tmp_path):
    load_people(db)
    with db.begin() as c:
        c.execute(text("DELETE FROM player_alias WHERE player_id = 'ba607b88'"))
        c.execute(text("DELETE FROM player_source_id WHERE player_id = 'ba607b88'"))
        c.execute(text("DELETE FROM player WHERE id = 'ba607b88'"))
    rep = backfill_zip(
        db, make_zip(tmp_path / "z.zip", {FINAL: cricsheet_json(FINAL)}), tmp_path / "a"
    )
    assert any("ba607b88" in i["detail"] for i in rep.quarantined[FINAL])
    assert scalar(db, "SELECT count(*) FROM delivery") == 0
    assert scalar(db, "SELECT data_status FROM match") == "quarantined"


def test_revised_payload_deletes_dropped_balls(db, tmp_path):
    load_people(db)
    backfill_zip(db, make_zip(tmp_path / "1.zip", {FINAL: cricsheet_json(FINAL)}), tmp_path / "a")
    d = json.loads(cricsheet_json(FINAL))
    d["innings"][1]["overs"][-1]["deliveries"].pop()  # a revision that removes one ball
    rep = backfill_zip(
        db, make_zip(tmp_path / "2.zip", {FINAL: json.dumps(d).encode()}), tmp_path / "a"
    )
    assert rep.changes.by_table["delivery"].deleted == 1


def test_source_loader_does_not_override_resolved_match(db, tmp_path):
    """Cricsheet is one vote: once a merge/manual owns the match row it is not overwritten."""
    load_people(db)
    z = make_zip(tmp_path / "z.zip", {FINAL: cricsheet_json(FINAL)})
    backfill_zip(db, z, tmp_path / "a")
    with db.begin() as c:
        c.execute(text("UPDATE match SET resolved_from = 'vote', toss_decision = 'bat'"))
    rep = backfill_zip(db, z, tmp_path / "a", force=True)
    assert rep.changes.total == 0
    assert scalar(db, "SELECT toss_decision FROM match") == "bat"


def test_credits_load_and_2026_fallback(db, tmp_path):
    load_people(db)
    backfill_zip(db, make_zip(tmp_path / "z.zip", {FINAL: cricsheet_json(FINAL)}), tmp_path / "a")
    teams = tmp_path / "Teams"
    teams.mkdir()
    (teams / "royal-challengers-bengaluru_squad.csv").write_bytes(
        "﻿Name,Role,Foreign Player,Credit Points,Full Name\n"
        "Virat Kohli,Batter,False,9,\n"  # matched through names.csv alias
        "Rajat Patidar,Batter,False,8.5, RM Patidar\n"
        "Never Played,Bowler,False,5,N Played\n".encode()
    )
    with db.begin() as c:
        rep = load_credits(c, teams, 2025)
    assert rep.matched == 2 and [r.name for r in rep.unmatched] == ["Never Played"]
    with db.begin() as c:
        assert load_credits(c, teams, 2025).changes.total == 0
    with db.connect() as c:
        eff, credits = credits_for_season(c, 2026)
        assert eff == 2025 and str(credits["ba607b88"]) == "9.0"
        assert credits_for_season(c, 2024) == (None, {})
    assert scalar(db, "SELECT count(*) FROM season_credits WHERE season = 2026") == 0


def test_lake_export(db, tmp_path):
    load_people(db)
    backfill_zip(
        db,
        make_zip(tmp_path / "z.zip", {m: cricsheet_json(m) for m in ALL_MATCHES}),
        tmp_path / "a",
    )
    counts = export_lake(db, tmp_path / "lake")
    assert counts["matches"] == 4
    t = pq.read_table(tmp_path / "lake" / "deliveries.parquet")
    assert t.num_rows == counts["deliveries"] == scalar(db, "SELECT count(*) FROM delivery")
    assert "batting_team" in t.column_names
    assert (tmp_path / "lake" / "match_players.parquet").exists()
