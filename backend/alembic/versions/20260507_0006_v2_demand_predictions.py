"""Add V2.7 demand prediction snapshots.

Revision ID: 20260507_0006
Revises: 20260507_0005
Create Date: 2026-05-07

V2.7 stores the explainable demand model output per artist/year. The table is
intentionally a snapshot table: raw evidence and metrics remain in the evidence
layer, while this table stores normalized features, score components and
explanations used by the current model version.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260507_0006"
down_revision = "20260507_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the V2.7 artist demand prediction snapshot table."""
    op.create_table(
        "v2_artist_demand_predictions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="SET NULL"), nullable=True),
        sa.Column("artist_slug", sa.String(length=255), nullable=False),
        sa.Column("artist_name", sa.String(length=255), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("main_genre", sa.String(length=160), nullable=False, server_default="Unknown"),
        sa.Column("secondary_genres_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("popularity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("career_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("momentum_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("nexus_affinity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("demand_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("crowd_risk", sa.String(length=40), nullable=False, server_default="low"),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.Column("method", sa.String(length=120), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feature_payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("factor_payload_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("explanation_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("year", "artist_slug", name="uq_v2_artist_demand_year_artist"),
    )
    op.create_index("ix_v2_artist_demand_predictions_id", "v2_artist_demand_predictions", ["id"], unique=False)
    op.create_index("ix_v2_artist_demand_year_rank", "v2_artist_demand_predictions", ["year", "rank"], unique=False)
    op.create_index("ix_v2_artist_demand_year_score", "v2_artist_demand_predictions", ["year", "demand_score"], unique=False)
    op.create_index("ix_v2_artist_demand_artist_slug", "v2_artist_demand_predictions", ["artist_slug"], unique=False)
    op.create_index("ix_v2_artist_demand_genre", "v2_artist_demand_predictions", ["year", "main_genre"], unique=False)


def downgrade() -> None:
    """Drop the V2.7 demand prediction snapshot table."""
    op.drop_index("ix_v2_artist_demand_genre", table_name="v2_artist_demand_predictions")
    op.drop_index("ix_v2_artist_demand_artist_slug", table_name="v2_artist_demand_predictions")
    op.drop_index("ix_v2_artist_demand_year_score", table_name="v2_artist_demand_predictions")
    op.drop_index("ix_v2_artist_demand_year_rank", table_name="v2_artist_demand_predictions")
    op.drop_index("ix_v2_artist_demand_predictions_id", table_name="v2_artist_demand_predictions")
    op.drop_table("v2_artist_demand_predictions")
