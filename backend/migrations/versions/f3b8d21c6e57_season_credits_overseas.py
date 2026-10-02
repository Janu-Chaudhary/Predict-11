"""season_credits.overseas: the squad CSV's "Foreign Player" flag (null when the CSV has none)

Revision ID: f3b8d21c6e57
Revises: e1a7c3d90b42
Create Date: 2026-10-02 15:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "f3b8d21c6e57"
down_revision = "e1a7c3d90b42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("season_credits", sa.Column("overseas", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("season_credits", "overseas")
