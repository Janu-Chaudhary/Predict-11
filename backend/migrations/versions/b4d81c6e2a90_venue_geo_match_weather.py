"""conditions: venue coordinates + hourly match weather (E2 dew & weather)

- ``venue_geo``: WGS84 coordinates per canonical venue with a cited source
  (``p11 weather venues``; values in p11.ingest.weather.VENUE_GEO).
- ``match_weather``: Open-Meteo archive hourly weather (UTC hours, start -4 h .. +4 h) per IPL
  match (``p11 weather backfill``).

Revision ID: b4d81c6e2a90
Revises: 7c3e9a1f5b20
Create Date: 2026-10-02 13:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "b4d81c6e2a90"
down_revision = "7c3e9a1f5b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "venue_geo",
        sa.Column("venue_id", sa.Integer(), nullable=False),
        sa.Column("lat", sa.Numeric(8, 5), nullable=False),
        sa.Column("lon", sa.Numeric(8, 5), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["venue_id"], ["venue.id"]),
        sa.PrimaryKeyConstraint("venue_id"),
    )
    op.create_table(
        "match_weather",
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temperature_2m", sa.Numeric(5, 2), nullable=True),
        sa.Column("relative_humidity_2m", sa.Numeric(5, 2), nullable=True),
        sa.Column("dew_point_2m", sa.Numeric(5, 2), nullable=True),
        sa.Column("precipitation", sa.Numeric(6, 2), nullable=True),
        sa.Column("wind_speed_10m", sa.Numeric(6, 2), nullable=True),
        sa.Column("anchor_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_approx", sa.Boolean(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("grid_lat", sa.Numeric(8, 5), nullable=True),
        sa.Column("grid_lon", sa.Numeric(8, 5), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["match_id"], ["match.id"]),
        sa.PrimaryKeyConstraint("match_id", "time_utc"),
    )


def downgrade() -> None:
    op.drop_table("match_weather")
    op.drop_table("venue_geo")
