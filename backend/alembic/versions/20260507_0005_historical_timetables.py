"""Add V2.6 historical timetable slots.

Revision ID: 20260507_0005
Revises: 20260507_0004
Create Date: 2026-05-07

V2.6 turns the historical timetable images/manual transcriptions into a
normalized slot table. The model stores canonical room names, observed aliases,
artist/show fields, time ranges, headliner flags and source/confidence metadata.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260507_0005"
down_revision = "20260507_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create historical timetable slot table and query indexes."""
    op.create_table(
        "historical_timetable_slots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("event_day", sa.String(length=40), nullable=False),
        sa.Column("festival_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("date_label", sa.String(length=80), nullable=True),
        sa.Column("room_name", sa.String(length=160), nullable=False),
        sa.Column("room_slug", sa.String(length=160), nullable=False),
        sa.Column("observed_room_name", sa.String(length=160), nullable=True),
        sa.Column("room_aliases_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="SET NULL"), nullable=True),
        sa.Column("artist_slug", sa.String(length=255), nullable=True),
        sa.Column("artist_name", sa.String(length=255), nullable=False),
        sa.Column("show_name", sa.String(length=255), nullable=False),
        sa.Column("performance_type", sa.String(length=80), nullable=False, server_default="solo"),
        sa.Column("start_time", sa.String(length=5), nullable=False),
        sa.Column("end_time", sa.String(length=5), nullable=False),
        sa.Column("start_minutes", sa.Integer(), nullable=False),
        sa.Column("end_minutes", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("slot_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("slot_type", sa.String(length=80), nullable=False, server_default="standard"),
        sa.Column("is_headliner_slot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_closing_slot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_warmup_slot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_special_show", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("extraction_method", sa.String(length=80), nullable=False, server_default="manual_image_transcription"),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="pending_review"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint(
            "year",
            "event_day",
            "room_slug",
            "start_minutes",
            "artist_slug",
            name="uq_historical_slot_identity",
        ),
    )
    op.create_index("ix_historical_timetable_slots_id", "historical_timetable_slots", ["id"], unique=False)
    op.create_index("ix_historical_slots_year_day", "historical_timetable_slots", ["year", "event_day"], unique=False)
    op.create_index(
        "ix_historical_slots_room_time",
        "historical_timetable_slots",
        ["year", "event_day", "room_slug", "start_minutes"],
        unique=False,
    )
    op.create_index("ix_historical_slots_artist", "historical_timetable_slots", ["artist_slug"], unique=False)
    op.create_index(
        "ix_historical_slots_headliner",
        "historical_timetable_slots",
        ["year", "is_headliner_slot"],
        unique=False,
    )


def downgrade() -> None:
    """Drop V2.6 historical timetable table."""
    op.drop_index("ix_historical_slots_headliner", table_name="historical_timetable_slots")
    op.drop_index("ix_historical_slots_artist", table_name="historical_timetable_slots")
    op.drop_index("ix_historical_slots_room_time", table_name="historical_timetable_slots")
    op.drop_index("ix_historical_slots_year_day", table_name="historical_timetable_slots")
    op.drop_index("ix_historical_timetable_slots_id", table_name="historical_timetable_slots")
    op.drop_table("historical_timetable_slots")
