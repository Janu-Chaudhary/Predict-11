"""merge Deccan Chargers into Sunrisers Hyderabad

Owner decision (2026-10-02): treat Hyderabad as one team history. Repoints every reference from
the Deccan Chargers team row to Sunrisers Hyderabad and keeps "Deccan Chargers" as an alias.
No-op on a database where Deccan Chargers was never loaded as its own team.

Revision ID: d975d2510448
Revises: 0f0a66354678
Create Date: 2026-10-02 00:47:37.868404
"""

from alembic import op

revision = "d975d2510448"
down_revision = "0f0a66354678"
branch_labels = None
depends_on = None

TEAM_REFS = [
    ("innings", "team_id"),
    ("match", "team1_id"),
    ("match", "team2_id"),
    ("match", "toss_winner_id"),
    ("match", "winner_id"),
    ("match_player", "team_id"),
    ("season_credits", "team_id"),
    ("team_alias", "team_id"),
]


def upgrade() -> None:
    op.execute("INSERT INTO team (name) VALUES ('Sunrisers Hyderabad') ON CONFLICT (name) DO NOTHING")
    for table, col in TEAM_REFS:
        op.execute(
            f"""
            UPDATE {table} SET {col} = (SELECT id FROM team WHERE name = 'Sunrisers Hyderabad')
            WHERE {col} = (SELECT id FROM team WHERE name = 'Deccan Chargers')
            """
        )
    op.execute("DELETE FROM team WHERE name = 'Deccan Chargers'")
    op.execute(
        "INSERT INTO team_alias (alias, team_id) "
        "SELECT 'Deccan Chargers', id FROM team WHERE name = 'Sunrisers Hyderabad' "
        "ON CONFLICT (alias) DO NOTHING"
    )


def downgrade() -> None:
    # The merge is lossy (which matches were Deccan's is only recoverable from the raw payloads):
    # downgrade by re-running the backfill with the old TEAM_RENAMES.
    pass
