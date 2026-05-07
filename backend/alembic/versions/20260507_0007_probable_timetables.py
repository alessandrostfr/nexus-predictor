"""Add V2.8 probable timetable slots.

Revision ID: 20260507_0007
Revises: 20260507_0006
Create Date: 2026-05-07

V2.8 stores the predicted, non-official 2026 timetable. The table keeps room,
time, artist, demand-score snapshot, confidence and reason payloads so the API
can clearly explain why a probable room/slot was assigned while still making it
explicit that this is not an official Fabrik/Nexus schedule.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260507_0007"
down_revision = "20260507_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the V2.8 probable timetable slot table."""
    op.create_table(
        "v2_probable_timetable_slots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("timetable_kind", sa.String(length=80), nullable=False, server_default="probable"),
        sa.Column("event_day", sa.String(length=40), nullable=False),
        sa.Column("festival_day", sa.Integer(), nullable=False),
        sa.Column("date_label", sa.String(length=120), nullable=True),
        sa.Column("room_name", sa.String(length=160), nullable=False),
        sa.Column("room_slug", sa.String(length=160), nullable=False),
        sa.Column("room_capacity", sa.Integer(), nullable=True),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="SET NULL"), nullable=True),
        sa.Column("artist_slug", sa.String(length=255), nullable=False),
        sa.Column("artist_name", sa.String(length=255), nullable=False),
        sa.Column("artist_rank", sa.Integer(), nullable=True),
        sa.Column("show_name", sa.String(length=255), nullable=False),
        sa.Column("performance_type", sa.String(length=80), nullable=False, server_default="solo"),
        sa.Column("main_genre", sa.String(length=160), nullable=False, server_default="Unknown"),
        sa.Column("secondary_genres_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("start_time", sa.String(length=5), nullable=False),
        sa.Column("end_time", sa.String(length=5), nullable=False),
        sa.Column("start_minutes", sa.Integer(), nullable=False),
        sa.Column("end_minutes", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("slot_order", sa.Integer(), nullable=False),
        sa.Column("slot_type", sa.String(length=80), nullable=False, server_default="standard"),
        sa.Column("is_headliner_slot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_closing_slot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_warmup_slot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_special_show", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("popularity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("career_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("momentum_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("nexus_affinity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("demand_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("expected_pressure_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("probability_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("crowd_risk", sa.String(length=40), nullable=False, server_default="low"),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.Column("method", sa.String(length=160), nullable=False),
        sa.Column("official_status", sa.String(length=80), nullable=False, server_default="predicted_not_official"),
        sa.Column("source_status", sa.String(length=80), nullable=False, server_default="no_official_timetable_yet"),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("warning_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("historical_pattern_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("year", "artist_slug", name="uq_v2_probable_timetable_year_artist"),
        sa.UniqueConstraint(
            "year",
            "event_day",
            "room_slug",
            "start_minutes",
            name="uq_v2_probable_timetable_room_slot",
        ),
    )
    op.create_index("ix_v2_probable_timetable_slots_id", "v2_probable_timetable_slots", ["id"], unique=False)
    op.create_index("ix_v2_probable_timetable_year_day", "v2_probable_timetable_slots", ["year", "event_day"], unique=False)
    op.create_index("ix_v2_probable_timetable_room_time", "v2_probable_timetable_slots", ["year", "event_day", "room_slug", "start_minutes"], unique=False)
    op.create_index("ix_v2_probable_timetable_artist", "v2_probable_timetable_slots", ["artist_slug"], unique=False)
    op.create_index("ix_v2_probable_timetable_rank", "v2_probable_timetable_slots", ["year", "artist_rank"], unique=False)
    op.create_index("ix_v2_probable_timetable_confidence", "v2_probable_timetable_slots", ["year", "confidence"], unique=False)


def downgrade() -> None:
    """Drop the V2.8 probable timetable table."""
    op.drop_index("ix_v2_probable_timetable_confidence", table_name="v2_probable_timetable_slots")
    op.drop_index("ix_v2_probable_timetable_rank", table_name="v2_probable_timetable_slots")
    op.drop_index("ix_v2_probable_timetable_artist", table_name="v2_probable_timetable_slots")
    op.drop_index("ix_v2_probable_timetable_room_time", table_name="v2_probable_timetable_slots")
    op.drop_index("ix_v2_probable_timetable_year_day", table_name="v2_probable_timetable_slots")
    op.drop_index("ix_v2_probable_timetable_slots_id", table_name="v2_probable_timetable_slots")
    op.drop_table("v2_probable_timetable_slots")
