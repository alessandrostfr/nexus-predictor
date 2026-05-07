"""Add V2.5 artist multi-genre table.

Revision ID: 20260507_0004
Revises: 20260507_0003
Create Date: 2026-05-07

The table stores one primary genre row and optional secondary genre rows per
artist. It complements the generic evidence layer: evidence_items stores why a
classification exists, while artist_genres gives fast filtering and frontend
chips.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260507_0004"
down_revision = "20260507_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the V2.5 artist_genres table."""
    op.create_table(
        "artist_genres",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="CASCADE"), nullable=True),
        sa.Column("artist_slug", sa.String(length=255), nullable=False),
        sa.Column("genre", sa.String(length=160), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source_summary_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_keys_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="inferred"),
        sa.Column("needs_manual_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("artist_slug", "genre", name="uq_artist_genres_artist_genre"),
    )
    op.create_index("ix_artist_genres_id", "artist_genres", ["id"], unique=False)
    op.create_index("ix_artist_genres_artist_id", "artist_genres", ["artist_id"], unique=False)
    op.create_index("ix_artist_genres_artist_slug", "artist_genres", ["artist_slug"], unique=False)
    op.create_index("ix_artist_genres_genre", "artist_genres", ["genre"], unique=False)
    op.create_index("ix_artist_genres_artist_primary", "artist_genres", ["artist_slug", "is_primary"], unique=False)
    op.create_index("ix_artist_genres_genre_primary", "artist_genres", ["genre", "is_primary"], unique=False)
    op.create_index("ix_artist_genres_confidence", "artist_genres", ["confidence", "confidence_score"], unique=False)


def downgrade() -> None:
    """Drop the V2.5 artist_genres table."""
    op.drop_index("ix_artist_genres_confidence", table_name="artist_genres")
    op.drop_index("ix_artist_genres_genre_primary", table_name="artist_genres")
    op.drop_index("ix_artist_genres_artist_primary", table_name="artist_genres")
    op.drop_index("ix_artist_genres_genre", table_name="artist_genres")
    op.drop_index("ix_artist_genres_artist_slug", table_name="artist_genres")
    op.drop_index("ix_artist_genres_artist_id", table_name="artist_genres")
    op.drop_index("ix_artist_genres_id", table_name="artist_genres")
    op.drop_table("artist_genres")
