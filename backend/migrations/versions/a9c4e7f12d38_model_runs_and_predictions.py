"""model_run + player_match_prediction: fantasy-points model versions and their predictions

- ``model_run``: one row per trained model version (params, metrics, features, size, and the
  full Model Lab ``telemetry`` document).
- ``player_match_prediction``: per (version, match, player) mean and p10/p50/p90 points plus the
  last-5-form baseline, tagged with the evaluation phase it was produced in (cv / test /
  walkforward).

Revision ID: a9c4e7f12d38
Revises: f3b8d21c6e57
Create Date: 2026-10-02 16:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a9c4e7f12d38"
down_revision = "f3b8d21c6e57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_run",
        sa.Column("version", sa.Text(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("params", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("n_learned_values", sa.Integer(), nullable=False),
        sa.Column("telemetry", postgresql.JSONB()),
        sa.Column("notes", sa.Text()),
    )
    op.create_table(
        "player_match_prediction",
        sa.Column(
            "model_version",
            sa.Text(),
            sa.ForeignKey("model_run.version", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("match_id", sa.BigInteger(), sa.ForeignKey("match.id"), nullable=False),
        sa.Column("player_id", sa.Text(), sa.ForeignKey("player.id"), nullable=False),
        sa.Column("phase", sa.Text(), nullable=False),
        sa.Column("mean", sa.Numeric(7, 2), nullable=False),
        sa.Column("p10", sa.Numeric(7, 2), nullable=False),
        sa.Column("p50", sa.Numeric(7, 2), nullable=False),
        sa.Column("p90", sa.Numeric(7, 2), nullable=False),
        sa.Column("baseline", sa.Numeric(7, 2)),
        sa.PrimaryKeyConstraint("model_version", "match_id", "player_id"),
        sa.CheckConstraint("phase IN ('cv', 'test', 'walkforward')", name="ck_pmpred_phase"),
    )
    op.create_index("ix_pmpred_match", "player_match_prediction", ["match_id"])


def downgrade() -> None:
    op.drop_index("ix_pmpred_match", table_name="player_match_prediction")
    op.drop_table("player_match_prediction")
    op.drop_table("model_run")
