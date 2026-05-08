"""Add V3.1 event contracts and continuous time windows.

Revision ID: 20260508_0009
Revises: 20260507_0008
Create Date: 2026-05-08

V3.1 introduces a durable event contract for Nexus 2026. The important product
correction is that 2026 is one continuous 18-hour event from 2026-06-13 12:00 to
2026-06-14 06:00, not two separated Friday/Saturday days.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260508_0009"
down_revision = "20260507_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create V3.1 event-contract tables."""
    op.create_table(
        "event_contracts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False, server_default="festival"),
        sa.Column("venue", sa.String(length=255), nullable=False, server_default="Fabrik Madrid"),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=80), nullable=False, server_default="Europe/Madrid"),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("start_label", sa.String(length=40), nullable=False),
        sa.Column("end_label", sa.String(length=40), nullable=False),
        sa.Column("duration_hours", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("continuous_event", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("functional_day_key", sa.String(length=80), nullable=False, server_default="nexus_day"),
        sa.Column("visible_label", sa.String(length=160), nullable=False, server_default="Evento continuo"),
        sa.Column("source_status", sa.String(length=80), nullable=False, server_default="researched_event_contract"),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="high"),
        sa.Column("extraction_method", sa.String(length=80), nullable=False, server_default="manual_researched_contract"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("peak_windows_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("year", name="uq_event_contracts_year"),
    )
    op.create_index("ix_event_contracts_id", "event_contracts", ["id"], unique=False)
    op.create_index("ix_event_contracts_event_key", "event_contracts", ["event_key"], unique=False)
    op.create_index("ix_event_contracts_year_continuous", "event_contracts", ["year", "continuous_event"], unique=False)

    op.create_table(
        "event_time_windows",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("event_contract_id", sa.Integer(), sa.ForeignKey("event_contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("window_index", sa.Integer(), nullable=False),
        sa.Column("window_key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("start_time", sa.String(length=5), nullable=False),
        sa.Column("end_time", sa.String(length=5), nullable=False),
        sa.Column("start_minutes_from_event_start", sa.Integer(), nullable=False),
        sa.Column("end_minutes_from_event_start", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("crosses_midnight", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("functional_day_key", sa.String(length=80), nullable=False, server_default="nexus_day"),
        sa.Column("slot_type", sa.String(length=80), nullable=False, server_default="standard"),
        sa.Column("is_peak_window", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evidence_status", sa.String(length=80), nullable=False, server_default="contract_window"),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="high"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("year", "window_key", name="uq_event_time_windows_year_key"),
    )
    op.create_index("ix_event_time_windows_id", "event_time_windows", ["id"], unique=False)
    op.create_index("ix_event_time_windows_contract_order", "event_time_windows", ["event_contract_id", "window_index"], unique=False)
    op.create_index("ix_event_time_windows_year_start", "event_time_windows", ["year", "start_minutes_from_event_start"], unique=False)


def downgrade() -> None:
    """Drop V3.1 event-contract tables."""
    op.drop_index("ix_event_time_windows_year_start", table_name="event_time_windows")
    op.drop_index("ix_event_time_windows_contract_order", table_name="event_time_windows")
    op.drop_index("ix_event_time_windows_id", table_name="event_time_windows")
    op.drop_table("event_time_windows")

    op.drop_index("ix_event_contracts_year_continuous", table_name="event_contracts")
    op.drop_index("ix_event_contracts_event_key", table_name="event_contracts")
    op.drop_index("ix_event_contracts_id", table_name="event_contracts")
    op.drop_table("event_contracts")
