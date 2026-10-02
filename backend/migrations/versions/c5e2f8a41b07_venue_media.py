"""venue_media: one freely licensed ground photo per venue (Wikimedia Commons)

``p11 media venues`` reads the curated ``data/raw/media/venue_images.json``, downloads each chosen
Commons original once and writes two WebP crops under web/public/venues/ (1600x600 cover,
640x400 card). Each row keeps the attribution the CC licences require: author, licence, licence
URL and the Commons file page.

Revision ID: c5e2f8a41b07
Revises: a9c4e7f12d38
Create Date: 2026-10-02 18:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "c5e2f8a41b07"
down_revision = "a9c4e7f12d38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "venue_media",
        sa.Column("venue_id", sa.Integer(), nullable=False),
        sa.Column("image_path", sa.Text(), nullable=False),
        sa.Column("thumb_path", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("file_page", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("license", sa.Text(), nullable=False),
        sa.Column("license_url", sa.Text(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["venue_id"], ["venue.id"]),
        sa.PrimaryKeyConstraint("venue_id"),
    )


def downgrade() -> None:
    op.drop_table("venue_media")
