"""Add Spotify artist cache table.

Revision ID: 20260507_0003
Revises: 20260507_0002
Create Date: 2026-05-07

V2.2 stores Spotify matches, public artist profile fields, top tracks and recent
releases in PostgreSQL. Evidence and metrics are still stored in the generic V2
evidence layer so model features remain traceable.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260507_0003"
down_revision = "20260507_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the Spotify cache table."""
    op.create_table(
        "spotify_artist_cache",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="CASCADE"), nullable=True),
        sa.Column("artist_slug", sa.String(length=255), nullable=False),
        sa.Column("spotify_artist_id", sa.String(length=255), nullable=False),
        sa.Column("spotify_url", sa.Text(), nullable=True),
        sa.Column("spotify_uri", sa.String(length=255), nullable=True),
        sa.Column("embed_url", sa.Text(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("popularity", sa.Integer(), nullable=True),
        sa.Column("followers", sa.Integer(), nullable=True),
        sa.Column("genres_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("top_tracks_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("releases_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("match_confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("match_method", sa.String(length=80), nullable=False, server_default="spotify_search"),
        sa.Column("last_refreshed_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("artist_slug", name="uq_spotify_artist_cache_artist_slug"),
        sa.UniqueConstraint("spotify_artist_id", name="uq_spotify_artist_cache_spotify_artist_id"),
    )
    op.create_index("ix_spotify_artist_cache_id", "spotify_artist_cache", ["id"], unique=False)
    op.create_index("ix_spotify_artist_cache_artist_slug", "spotify_artist_cache", ["artist_slug"], unique=False)
    op.create_index("ix_spotify_artist_cache_popularity", "spotify_artist_cache", ["popularity"], unique=False)
    op.create_index(
        "ix_spotify_artist_cache_match_confidence",
        "spotify_artist_cache",
        ["match_confidence"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the Spotify cache table."""
    op.drop_index("ix_spotify_artist_cache_match_confidence", table_name="spotify_artist_cache")
    op.drop_index("ix_spotify_artist_cache_popularity", table_name="spotify_artist_cache")
    op.drop_index("ix_spotify_artist_cache_artist_slug", table_name="spotify_artist_cache")
    op.drop_index("ix_spotify_artist_cache_id", table_name="spotify_artist_cache")
    op.drop_table("spotify_artist_cache")
