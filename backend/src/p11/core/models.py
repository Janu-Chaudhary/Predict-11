"""Canonical Postgres schema (SQLAlchemy 2 ORM models).

Identity rules:
- ``player.id`` is the Cricsheet register identifier (8 hex chars). Every other source's player
  key is mapped to it through ``player_source_id``; joins never use names.
- ``match.id`` is the ESPNcricinfo object id, which is also the Cricsheet file id; per-source ids
  live in their own columns so scraped matches can be attached to the same row later.
- Teams and venues have one canonical row each plus an alias table holding every raw spelling
  seen in any source (franchise renames, "Stadium" vs "Stadium, City").

Multi-source design: Cricsheet is *one vote*, not the truth. Every source keeps its own copy of a
match (``match_source`` + per-source ``innings`` / ``match_player`` / ``delivery`` rows keyed by
``source``). The ``match`` row holds the currently *resolved* match-level facts and
``match.ball_source`` names which source's ball-by-ball copy is resolved (a future majority-vote
merger will write its output as source ``"merged"`` and point ``ball_source`` at it). Per-field
disagreements are recorded in ``field_conflict``. Views ``delivery_resolved`` /
``match_player_resolved`` / ``innings_resolved`` expose the resolved copy to consumers.

All loaders upsert on natural keys (ON CONFLICT ... DO UPDATE ... WHERE IS DISTINCT FROM), so a
re-run with identical input writes zero rows.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

# single_source: exactly one non-quarantined source copy; unverified: >=2 copies not yet
# cross-checked; verified: cross-checker found no disagreement; conflict: open field_conflict
# rows; quarantined: every source copy failed DQ. See p11.ingest.store.refresh_match_status.
MATCH_STATUSES = ("single_source", "unverified", "verified", "conflict", "quarantined")
SOURCE_STATUSES = ("loaded", "quarantined")
ROLES_IN_MATCH = ("xi", "impact_in", "impact_out", "sub", "sub_fielder")


# --------------------------------------------------------------------------- registry
class Player(Base):
    __tablename__ = "player"
    id: Mapped[str] = mapped_column(Text, primary_key=True)  # cricsheet identifier
    name: Mapped[str] = mapped_column(Text)  # cricsheet short name, e.g. "V Kohli"
    unique_name: Mapped[str] = mapped_column(Text)


class PlayerAlias(Base):
    __tablename__ = "player_alias"
    player_id: Mapped[str] = mapped_column(ForeignKey("player.id"), primary_key=True)
    name: Mapped[str] = mapped_column(Text, primary_key=True)
    source: Mapped[str] = mapped_column(Text)  # cricsheet_names | manual | <scraper>
    __table_args__ = (Index("ix_player_alias_lower_name", func.lower(name)),)


class PlayerSourceId(Base):
    __tablename__ = "player_source_id"
    player_id: Mapped[str] = mapped_column(ForeignKey("player.id"), primary_key=True)
    source: Mapped[str] = mapped_column(Text, primary_key=True)  # cricinfo|cricbuzz|bcci|pulse..
    source_key: Mapped[str] = mapped_column(Text, primary_key=True)
    __table_args__ = (UniqueConstraint("source", "source_key", name="uq_player_source_key"),)


class Team(Base):
    __tablename__ = "team"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True)  # current franchise name


class TeamAlias(Base):
    __tablename__ = "team_alias"
    alias: Mapped[str] = mapped_column(Text, primary_key=True)  # raw spelling from any source
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))


class Venue(Base):
    __tablename__ = "venue"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    city: Mapped[str | None] = mapped_column(Text)


class VenueAlias(Base):
    __tablename__ = "venue_alias"
    alias: Mapped[str] = mapped_column(Text, primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venue.id"))


class Competition(Base):
    __tablename__ = "competition"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Text, unique=True)  # "ipl"
    name: Mapped[str] = mapped_column(Text)


class Season(Base):
    __tablename__ = "season"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competition.id"))
    year: Mapped[int] = mapped_column(Integer)  # calendar year the season was played in
    label: Mapped[str] = mapped_column(Text)  # source label, e.g. "2020/21"
    __table_args__ = (UniqueConstraint("competition_id", "year", name="uq_season"),)


class SeasonCredits(Base):
    """Dream11 credits are fixed per player per season (IPL only, so keyed by year).

    Missing seasons fall back at query time (see ``p11.registry.credits``), rows are never copied.
    """

    __tablename__ = "season_credits"
    season: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("player.id"), primary_key=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"))
    credits: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    source: Mapped[str] = mapped_column(Text)


# --------------------------------------------------------------------------- raw archive
class RawPayload(Base):
    __tablename__ = "raw_payload"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(Text)
    url_or_file: Mapped[str] = mapped_column(Text)  # e.g. "ipl_json.zip!1529281.json"
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    sha256: Mapped[str] = mapped_column(Text)
    archive_path: Mapped[str | None] = mapped_column(Text)  # gzipped copy under data/archive
    parse_status: Mapped[str] = mapped_column(Text)  # pending|loaded|quarantined|error
    detail: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("source", "sha256", name="uq_raw_payload_sha"),)


# --------------------------------------------------------------------------- matches
class Match(Base):
    """Resolved match-level facts. ``resolved_from`` says who last wrote them: a single-source
    loader (e.g. "cricsheet") may refresh them only while it is still the resolver; once a
    vote/manual resolution owns the row, source loaders leave it alone."""

    __tablename__ = "match"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    cricsheet_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    cricinfo_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    cricbuzz_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    bcci_id: Mapped[str | None] = mapped_column(Text, unique=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id"))
    start_date: Mapped[dt.date] = mapped_column(Date)
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venue.id"))
    city: Mapped[str | None] = mapped_column(Text)
    team1_id: Mapped[int] = mapped_column(ForeignKey("team.id"))
    team2_id: Mapped[int] = mapped_column(ForeignKey("team.id"))
    toss_winner_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"))
    toss_decision: Mapped[str | None] = mapped_column(Text)  # bat|field
    result: Mapped[str] = mapped_column(Text)  # win|tie|no_result
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"))  # incl. super-over winner
    win_by_runs: Mapped[int | None] = mapped_column(Integer)
    win_by_wickets: Mapped[int | None] = mapped_column(Integer)
    method: Mapped[str | None] = mapped_column(Text)  # "D/L" etc.
    match_number: Mapped[int | None] = mapped_column(Integer)
    stage: Mapped[str | None] = mapped_column(Text)  # Final, Qualifier 1, ...
    overs: Mapped[int] = mapped_column(SmallInteger, default=20)
    player_of_match: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    resolved_from: Mapped[str] = mapped_column(Text)  # cricsheet|bcci|...|vote|manual
    ball_source: Mapped[str | None] = mapped_column(Text)  # source whose balls are resolved
    data_status: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint("data_status IN " + str(MATCH_STATUSES), name="ck_match_data_status"),
        Index("ix_match_season_date", "season_id", "start_date"),
    )


class MatchSource(Base):
    """One row per (match, source) copy: provenance, revision and DQ outcome of that copy."""

    __tablename__ = "match_source"
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id"), primary_key=True)
    source: Mapped[str] = mapped_column(Text, primary_key=True)
    source_match_key: Mapped[str] = mapped_column(Text)
    raw_payload_id: Mapped[int | None] = mapped_column(ForeignKey("raw_payload.id"))
    revision: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text)
    dq_issues: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    facts: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # this source's match-level view
    __table_args__ = (
        CheckConstraint("status IN " + str(SOURCE_STATUSES), name="ck_match_source_status"),
    )


class Innings(Base):
    __tablename__ = "innings"
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id"), primary_key=True)
    source: Mapped[str] = mapped_column(Text, primary_key=True)
    innings: Mapped[int] = mapped_column(SmallInteger, primary_key=True)  # 1,2; super overs 3..
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))
    super_over: Mapped[bool] = mapped_column(Boolean)
    target_runs: Mapped[int | None] = mapped_column(Integer)
    target_overs: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    absent_hurt: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    __table_args__ = (
        ForeignKeyConstraint(
            ["match_id", "source"],
            ["match_source.match_id", "match_source.source"],
            name="fk_innings_match_source",
        ),
    )


class MatchPlayer(Base):
    __tablename__ = "match_player"
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id"), primary_key=True)
    source: Mapped[str] = mapped_column(Text, primary_key=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("player.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))
    role_in_match: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint("role_in_match IN " + str(ROLES_IN_MATCH), name="ck_match_player_role"),
        ForeignKeyConstraint(
            ["match_id", "source"],
            ["match_source.match_id", "match_source.source"],
            name="fk_match_player_match_source",
        ),
        Index("ix_match_player_player", "player_id"),
    )


class Delivery(Base):
    __tablename__ = "delivery"
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id"), primary_key=True)
    source: Mapped[str] = mapped_column(Text, primary_key=True)
    innings: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    ball_seq: Mapped[int] = mapped_column(SmallInteger, primary_key=True)  # 1.. within innings
    super_over: Mapped[bool] = mapped_column(Boolean)
    over: Mapped[int] = mapped_column(SmallInteger)  # 0-based, as in Cricsheet
    ball_in_over: Mapped[int] = mapped_column(SmallInteger)  # 1-based incl. wides/no-balls
    batter_id: Mapped[str] = mapped_column(ForeignKey("player.id"))
    bowler_id: Mapped[str] = mapped_column(ForeignKey("player.id"))
    non_striker_id: Mapped[str] = mapped_column(ForeignKey("player.id"))
    batter_runs: Mapped[int] = mapped_column(SmallInteger)
    extras: Mapped[int] = mapped_column(SmallInteger)
    total_runs: Mapped[int] = mapped_column(SmallInteger)
    extra_type: Mapped[str | None] = mapped_column(Text)  # wides|noballs|byes|legbyes|penalty
    wides: Mapped[int] = mapped_column(SmallInteger, default=0)
    noballs: Mapped[int] = mapped_column(SmallInteger, default=0)
    byes: Mapped[int] = mapped_column(SmallInteger, default=0)
    legbyes: Mapped[int] = mapped_column(SmallInteger, default=0)
    penalty: Mapped[int] = mapped_column(SmallInteger, default=0)
    non_boundary: Mapped[bool] = mapped_column(Boolean, default=False)
    wicket_kind: Mapped[str | None] = mapped_column(Text)
    player_out_id: Mapped[str | None] = mapped_column(ForeignKey("player.id"))
    fielder_ids: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    __table_args__ = (
        ForeignKeyConstraint(
            ["match_id", "source", "innings"],
            ["innings.match_id", "innings.source", "innings.innings"],
            name="fk_delivery_innings",
        ),
        Index("ix_delivery_batter", "batter_id"),
        Index("ix_delivery_bowler", "bowler_id"),
    )


class FieldConflict(Base):
    """A disagreement between sources on one field. ``scope`` is match|innings|delivery|
    match_player; innings/ball_seq/player_id are NULL where not applicable. ``source_values``
    maps source -> value; the (future) vote fills ``resolved_value``/``resolution``."""

    __tablename__ = "field_conflict"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id"))
    scope: Mapped[str] = mapped_column(Text)
    innings: Mapped[int | None] = mapped_column(SmallInteger)
    ball_seq: Mapped[int | None] = mapped_column(SmallInteger)
    player_id: Mapped[str | None] = mapped_column(Text)
    field: Mapped[str] = mapped_column(Text)
    source_values: Mapped[dict[str, Any]] = mapped_column(JSONB)
    resolved_value: Mapped[Any | None] = mapped_column(JSONB)
    resolution: Mapped[str | None] = mapped_column(Text)  # majority|priority|manual
    status: Mapped[str] = mapped_column(Text, default="open")  # open|resolved
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "scope",
            "innings",
            "ball_seq",
            "player_id",
            "field",
            name="uq_field_conflict",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint("status IN ('open', 'resolved')", name="ck_field_conflict_status"),
    )
