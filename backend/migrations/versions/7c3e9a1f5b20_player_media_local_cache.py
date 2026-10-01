"""player_media: locally cached WebP copies of each headshot

``p11 media cache`` downloads each resolved headshot once and writes 256 px / 96 px WebP files
under web/public/players/. ``cached_url`` records which ``image_url`` the files were made from,
so a changed source URL makes the view stop exposing the stale local copy until re-cached.

Revision ID: 7c3e9a1f5b20
Revises: 46ea0beec0d4
Create Date: 2026-10-02 12:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "7c3e9a1f5b20"
down_revision = "46ea0beec0d4"
branch_labels = None
depends_on = None

OLD_VIEW = """
CREATE VIEW player_media_resolved AS
SELECT DISTINCT ON (player_id) player_id, image_url, source AS image_source, image_season
FROM player_media
ORDER BY player_id, image_season DESC, CASE source WHEN 'bcci' THEN 1 ELSE 2 END
"""

NEW_VIEW = """
CREATE VIEW player_media_resolved AS
SELECT DISTINCT ON (player_id) player_id, image_url, source AS image_source, image_season,
       CASE WHEN cached_url = image_url THEN local_path END AS local_path,
       CASE WHEN cached_url = image_url THEN local_thumb_path END AS local_thumb_path
FROM player_media
ORDER BY player_id, image_season DESC, CASE source WHEN 'bcci' THEN 1 ELSE 2 END
"""


def upgrade() -> None:
    op.add_column("player_media", sa.Column("cached_url", sa.Text(), nullable=True))
    op.add_column("player_media", sa.Column("local_path", sa.Text(), nullable=True))
    op.add_column("player_media", sa.Column("local_thumb_path", sa.Text(), nullable=True))
    op.add_column(
        "player_media", sa.Column("cached_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("DROP VIEW IF EXISTS player_media_resolved")
    op.execute(NEW_VIEW)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS player_media_resolved")
    op.execute(OLD_VIEW)
    for col in ("cached_at", "local_thumb_path", "local_path", "cached_url"):
        op.drop_column("player_media", col)
