"""step0: player attributes + media, match start time, player match points

- ``player_attribute``: role / batting hand / bowling style per (player, source), plus the
  ``player_attribute_resolved`` view (per field: first non-null by source priority).
- ``player_media``: headshot URL per (player, source), plus ``player_media_resolved``.
- ``match.start_time_utc`` / ``day_night`` / ``start_time_source``.
- ``player_match_points``: persisted Dream11 points per (match, player); ``computed_at`` is
  bumped by a trigger only when a recompute really changes the row.

Revision ID: 46ea0beec0d4
Revises: d975d2510448
Create Date: 2026-10-02 01:45:07.860755
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "46ea0beec0d4"
down_revision = "d975d2510448"
branch_labels = None
depends_on = None

# Frozen copies of p11.registry.attributes.ROLE_PRIORITY / STYLE_PRIORITY at this revision.
ROLE_PRIORITY = ("bcci", "iplt20_2025", "cricinfo", "espn_api", "cricbuzz", "derived")
STYLE_PRIORITY = ("cricinfo", "espn_api", "bcci", "cricbuzz", "iplt20_2025", "derived")


def _case(prio: tuple[str, ...]) -> str:
    whens = " ".join(f"WHEN '{s}' THEN {i}" for i, s in enumerate(prio, start=1))
    return f"CASE a.source {whens} ELSE 99 END"


def _pick(col: str, prio: str, what: str | None = None) -> str:
    what = what or f"a.{col}"
    return (
        f"(array_agg({what} ORDER BY {prio}, a.as_of DESC) "
        f"FILTER (WHERE a.{col} IS NOT NULL))[1]"
    )


ATTR_VIEW = f"""
CREATE VIEW player_attribute_resolved AS
SELECT a.player_id,
       {_pick("playing_role", _case(ROLE_PRIORITY))} AS playing_role,
       {_pick("playing_role", _case(ROLE_PRIORITY), "a.source")} AS role_source,
       {_pick("batting_hand", _case(STYLE_PRIORITY))} AS batting_hand,
       {_pick("batting_hand", _case(STYLE_PRIORITY), "a.source")} AS batting_hand_source,
       {_pick("bowling_type", _case(STYLE_PRIORITY), "a.bowling_style")} AS bowling_style,
       {_pick("bowling_type", _case(STYLE_PRIORITY))} AS bowling_type,
       {_pick("bowling_type", _case(STYLE_PRIORITY), "a.source")} AS bowling_source
FROM player_attribute a
GROUP BY a.player_id
"""

MEDIA_VIEW = """
CREATE VIEW player_media_resolved AS
SELECT DISTINCT ON (player_id) player_id, image_url, source AS image_source, image_season
FROM player_media
ORDER BY player_id, image_season DESC, CASE source WHEN 'bcci' THEN 1 ELSE 2 END
"""


def upgrade() -> None:
    op.create_table(
        "player_attribute",
        sa.Column("player_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("playing_role", sa.Text(), nullable=True),
        sa.Column("source_role", sa.Text(), nullable=True),
        sa.Column("batting_hand", sa.Text(), nullable=True),
        sa.Column("bowling_style", sa.Text(), nullable=True),
        sa.Column("bowling_type", sa.Text(), nullable=True),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("batting_hand IN ('R', 'L')", name="ck_player_attr_hand"),
        sa.CheckConstraint(
            "bowling_type IN ('right-arm fast', 'right-arm medium', 'off-spin', 'leg-spin', "
            "'left-arm fast', 'left-arm medium', 'left-arm orthodox', 'left-arm wrist')",
            name="ck_player_attr_bowl",
        ),
        sa.CheckConstraint(
            "playing_role IN ('WK', 'BAT', 'AR', 'BOWL')", name="ck_player_attr_role"
        ),
        sa.ForeignKeyConstraint(["player_id"], ["player.id"]),
        sa.PrimaryKeyConstraint("player_id", "source"),
    )
    op.create_table(
        "player_media",
        sa.Column("player_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("image_season", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["player_id"], ["player.id"]),
        sa.PrimaryKeyConstraint("player_id", "source"),
    )
    op.create_table(
        "player_match_points",
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.Text(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("rules_version", sa.Text(), nullable=False),
        sa.Column("role_used", sa.Text(), nullable=False),
        sa.Column("role_source", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("batting", sa.Integer(), nullable=False),
        sa.Column("bowling", sa.Integer(), nullable=False),
        sa.Column("fielding", sa.Integer(), nullable=False),
        sa.Column("lineup", sa.Integer(), nullable=False),
        sa.Column("bonuses", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role_used IN ('WK', 'BAT', 'AR', 'BOWL')", name="ck_pmp_role"),
        sa.CheckConstraint(
            "status IN ('xi', 'impact_in', 'impact_out', 'sub')", name="ck_pmp_status"
        ),
        sa.ForeignKeyConstraint(["match_id"], ["match.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["player.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"]),
        sa.PrimaryKeyConstraint("match_id", "player_id"),
    )
    op.create_index("ix_pmp_player", "player_match_points", ["player_id"], unique=False)
    op.add_column("match", sa.Column("start_time_utc", sa.DateTime(timezone=True), nullable=True))
    op.add_column("match", sa.Column("day_night", sa.Text(), nullable=True))
    op.add_column("match", sa.Column("start_time_source", sa.Text(), nullable=True))
    op.create_check_constraint("ck_match_day_night", "match", "day_night IN ('day', 'night')")

    op.execute(ATTR_VIEW)
    op.execute(MEDIA_VIEW)
    op.execute(
        """
        CREATE FUNCTION p11_touch_computed_at() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN NEW.computed_at := now(); RETURN NEW; END $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_pmp_touch BEFORE UPDATE ON player_match_points "
        "FOR EACH ROW EXECUTE FUNCTION p11_touch_computed_at()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_pmp_touch ON player_match_points")
    op.execute("DROP FUNCTION IF EXISTS p11_touch_computed_at()")
    op.execute("DROP VIEW IF EXISTS player_media_resolved")
    op.execute("DROP VIEW IF EXISTS player_attribute_resolved")
    op.drop_constraint("ck_match_day_night", "match", type_="check")
    op.drop_column("match", "start_time_source")
    op.drop_column("match", "day_night")
    op.drop_column("match", "start_time_utc")
    op.drop_index("ix_pmp_player", table_name="player_match_points")
    op.drop_table("player_match_points")
    op.drop_table("player_media")
    op.drop_table("player_attribute")
