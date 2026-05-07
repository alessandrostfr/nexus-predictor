"""Create initial V2 foundation tables.

Revision ID: 20260507_0001
Revises:
Create Date: 2026-05-07

This migration mirrors the stable V1 relational tables so the existing API can
keep working while V2 moves from SQLite-style local storage to PostgreSQL and
future evidence-oriented tables.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# Revision identifiers used by Alembic.
revision = "20260507_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the base tables used by the V1-compatible API."""
    op.create_table(
        "editions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("venue", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("date_start", sa.String(length=50), nullable=True),
        sa.Column("date_end", sa.String(length=50), nullable=True),
        sa.Column("duration_hours", sa.Integer(), nullable=True),
        sa.Column("artist_count", sa.Integer(), nullable=False),
        sa.Column("stage_count", sa.Integer(), nullable=False),
        sa.Column("attendance_json", sa.Text(), nullable=False),
        sa.Column("lineup_json", sa.Text(), nullable=False),
        sa.Column("sources_json", sa.Text(), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_editions_year", "editions", ["year"], unique=True)

    op.create_table(
        "artists",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("primary_genre_seed", sa.String(length=120), nullable=False),
        sa.Column("appearance_count", sa.Integer(), nullable=False),
        sa.Column("manual_review", sa.Boolean(), nullable=False),
        sa.Column("data_status", sa.String(length=120), nullable=False),
        sa.Column("appearance_years_json", sa.Text(), nullable=False),
        sa.Column("appearances_json", sa.Text(), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_artists_slug", "artists", ["slug"], unique=True)

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("min_capacity", sa.Integer(), nullable=True),
        sa.Column("estimated_capacity", sa.Integer(), nullable=True),
        sa.Column("max_capacity", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.String(length=80), nullable=False),
        sa.Column("aliases_json", sa.Text(), nullable=False),
        sa.Column("source_keys_json", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rooms_name", "rooms", ["name"], unique=True)

    op.create_table(
        "dataset_meta",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("key", name="uq_dataset_meta_key"),
    )


def downgrade() -> None:
    """Drop the base tables in reverse dependency order."""
    op.drop_table("dataset_meta")

    op.drop_index("ix_rooms_name", table_name="rooms")
    op.drop_table("rooms")

    op.drop_index("ix_artists_slug", table_name="artists")
    op.drop_table("artists")

    op.drop_index("ix_editions_year", table_name="editions")
    op.drop_table("editions")
