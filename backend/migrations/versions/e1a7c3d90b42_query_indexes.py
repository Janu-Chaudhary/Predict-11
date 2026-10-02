"""query indexes: delivery lookups by non-striker / dismissed player / fielder / pair, matches by
venue, trigram name search

- ``delivery(non_striker_id)``, partial ``delivery(player_out_id)`` (wickets only), GIN
  ``fielder_ids`` (catches / stumpings / run outs by fielder), ``delivery(batter_id, bowler_id)``
  (/h2h pairs).
- ``match(venue_id)`` (venue cards, toss trend, dew).
- ``pg_trgm`` GIN on ``player.name`` and ``player_alias.name`` for substring name search.

Revision ID: e1a7c3d90b42
Revises: b4d81c6e2a90
Create Date: 2026-10-02 14:00:00
"""

from alembic import op

revision = "e1a7c3d90b42"
down_revision = "b4d81c6e2a90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index("ix_delivery_non_striker", "delivery", ["non_striker_id"])
    op.create_index(
        "ix_delivery_player_out",
        "delivery",
        ["player_out_id"],
        postgresql_where="player_out_id IS NOT NULL",
    )
    op.create_index("ix_delivery_fielder_ids", "delivery", ["fielder_ids"], postgresql_using="gin")
    op.create_index("ix_delivery_batter_bowler", "delivery", ["batter_id", "bowler_id"])
    op.create_index("ix_match_venue", "match", ["venue_id"])
    op.execute("CREATE INDEX ix_player_name_trgm ON player USING gin (name gin_trgm_ops)")
    op.execute(
        "CREATE INDEX ix_player_alias_name_trgm ON player_alias USING gin (name gin_trgm_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_player_alias_name_trgm", table_name="player_alias")
    op.drop_index("ix_player_name_trgm", table_name="player")
    op.drop_index("ix_match_venue", table_name="match")
    op.drop_index("ix_delivery_batter_bowler", table_name="delivery")
    op.drop_index("ix_delivery_fielder_ids", table_name="delivery")
    op.drop_index("ix_delivery_player_out", table_name="delivery")
    op.drop_index("ix_delivery_non_striker", table_name="delivery")
    # pg_trgm is left installed: other objects may depend on it.
