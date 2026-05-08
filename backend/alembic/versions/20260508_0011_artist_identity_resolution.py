"""Add V3.3 artist identity resolution tables.

Revision ID: 20260508_0011
Revises: 20260508_0010
Create Date: 2026-05-08

V3.3 creates a canonical artist identity layer before external platform metrics
are used as ML features. This prevents Spotify, SoundCloud, YouTube or social
signals from being attached to the wrong artist.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260508_0011"
down_revision = "20260508_0010"
branch_labels = None
depends_on = None

JSON_OBJECT_DEFAULT = sa.text("'{}'::jsonb")


def upgrade() -> None:
    """Create V3.3 identity-resolution tables."""
    op.create_table(
        "artist_master",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="SET NULL"), nullable=True),
        sa.Column("canonical_artist_key", sa.String(length=255), nullable=False),
        sa.Column("source_artist_slug", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("primary_genre_seed", sa.String(length=160), nullable=True),
        sa.Column("appearance_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_2026_artist", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_top_artist", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("needs_manual_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("review_status", sa.String(length=60), nullable=False, server_default="seed_verified"),
        sa.Column("feature_eligibility_status", sa.String(length=80), nullable=False, server_default="internal_seed_only"),
        sa.Column("alias_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("appearances_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("canonical_artist_key", name="uq_artist_master_key"),
        sa.UniqueConstraint("source_artist_slug", name="uq_artist_master_source_slug"),
    )
    op.create_index("ix_artist_master_id", "artist_master", ["id"], unique=False)
    op.create_index("ix_artist_master_artist_id", "artist_master", ["artist_id"], unique=False)
    op.create_index("ix_artist_master_normalized_name", "artist_master", ["normalized_name"], unique=False)
    op.create_index("ix_artist_master_review_status", "artist_master", ["review_status", "needs_manual_review"], unique=False)

    op.create_table(
        "artist_aliases",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("artist_master_id", sa.Integer(), sa.ForeignKey("artist_master.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canonical_artist_key", sa.String(length=255), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("normalized_alias", sa.String(length=255), nullable=False),
        sa.Column("alias_type", sa.String(length=80), nullable=False, server_default="display_name"),
        sa.Column("source_key", sa.String(length=160), nullable=False, server_default="nexus_seed"),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="high"),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("artist_master_id", "normalized_alias", "alias_type", name="uq_artist_alias_identity"),
    )
    op.create_index("ix_artist_aliases_id", "artist_aliases", ["id"], unique=False)
    op.create_index("ix_artist_aliases_artist_master_id", "artist_aliases", ["artist_master_id"], unique=False)
    op.create_index("ix_artist_aliases_normalized", "artist_aliases", ["normalized_alias"], unique=False)
    op.create_index("ix_artist_aliases_confidence", "artist_aliases", ["confidence", "status"], unique=False)

    op.create_table(
        "artist_identity_links",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("artist_master_id", sa.Integer(), sa.ForeignKey("artist_master.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="SET NULL"), nullable=True),
        sa.Column("canonical_artist_key", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=80), nullable=False),
        sa.Column("profile_name", sa.String(length=255), nullable=True),
        sa.Column("normalized_profile_name", sa.String(length=255), nullable=True),
        sa.Column("profile_url", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("match_status", sa.String(length=60), nullable=False, server_default="pending_review"),
        sa.Column("match_method", sa.String(length=120), nullable=False, server_default="seed_match"),
        sa.Column("source_table", sa.String(length=120), nullable=True),
        sa.Column("source_record_id", sa.Integer(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_feature_eligible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("artist_master_id", "platform", "profile_url", name="uq_artist_identity_link_url"),
        sa.UniqueConstraint("artist_master_id", "platform", "external_id", name="uq_artist_identity_link_external_id"),
    )
    op.create_index("ix_artist_identity_links_id", "artist_identity_links", ["id"], unique=False)
    op.create_index("ix_artist_identity_links_artist_master_id", "artist_identity_links", ["artist_master_id"], unique=False)
    op.create_index("ix_artist_identity_links_artist_id", "artist_identity_links", ["artist_id"], unique=False)
    op.create_index("ix_artist_identity_links_platform_status", "artist_identity_links", ["platform", "match_status"], unique=False)
    op.create_index("ix_artist_identity_links_feature_eligible", "artist_identity_links", ["is_feature_eligible", "confidence"], unique=False)

    op.create_table(
        "artist_identity_candidates",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("artist_master_id", sa.Integer(), sa.ForeignKey("artist_master.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="SET NULL"), nullable=True),
        sa.Column("canonical_artist_key", sa.String(length=255), nullable=False),
        sa.Column("candidate_key", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=80), nullable=False),
        sa.Column("candidate_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_candidate_name", sa.String(length=255), nullable=False),
        sa.Column("candidate_url", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="pending_review"),
        sa.Column("suggested_action", sa.String(length=80), nullable=False, server_default="manual_review"),
        sa.Column("match_method", sa.String(length=120), nullable=False, server_default="name_similarity"),
        sa.Column("source_table", sa.String(length=120), nullable=True),
        sa.Column("source_record_id", sa.Integer(), nullable=True),
        sa.Column("evidence_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("candidate_key", name="uq_artist_identity_candidate_key"),
    )
    op.create_index("ix_artist_identity_candidates_id", "artist_identity_candidates", ["id"], unique=False)
    op.create_index("ix_artist_identity_candidates_artist_master_id", "artist_identity_candidates", ["artist_master_id"], unique=False)
    op.create_index("ix_artist_identity_candidates_status", "artist_identity_candidates", ["status", "confidence"], unique=False)
    op.create_index("ix_artist_identity_candidates_artist", "artist_identity_candidates", ["artist_master_id", "status"], unique=False)
    op.create_index("ix_artist_identity_candidates_platform", "artist_identity_candidates", ["platform", "status"], unique=False)


def downgrade() -> None:
    """Drop V3.3 identity-resolution tables in dependency-safe order."""
    op.drop_index("ix_artist_identity_candidates_platform", table_name="artist_identity_candidates")
    op.drop_index("ix_artist_identity_candidates_artist", table_name="artist_identity_candidates")
    op.drop_index("ix_artist_identity_candidates_status", table_name="artist_identity_candidates")
    op.drop_index("ix_artist_identity_candidates_artist_master_id", table_name="artist_identity_candidates")
    op.drop_index("ix_artist_identity_candidates_id", table_name="artist_identity_candidates")
    op.drop_table("artist_identity_candidates")

    op.drop_index("ix_artist_identity_links_feature_eligible", table_name="artist_identity_links")
    op.drop_index("ix_artist_identity_links_platform_status", table_name="artist_identity_links")
    op.drop_index("ix_artist_identity_links_artist_id", table_name="artist_identity_links")
    op.drop_index("ix_artist_identity_links_artist_master_id", table_name="artist_identity_links")
    op.drop_index("ix_artist_identity_links_id", table_name="artist_identity_links")
    op.drop_table("artist_identity_links")

    op.drop_index("ix_artist_aliases_confidence", table_name="artist_aliases")
    op.drop_index("ix_artist_aliases_normalized", table_name="artist_aliases")
    op.drop_index("ix_artist_aliases_artist_master_id", table_name="artist_aliases")
    op.drop_index("ix_artist_aliases_id", table_name="artist_aliases")
    op.drop_table("artist_aliases")

    op.drop_index("ix_artist_master_review_status", table_name="artist_master")
    op.drop_index("ix_artist_master_normalized_name", table_name="artist_master")
    op.drop_index("ix_artist_master_artist_id", table_name="artist_master")
    op.drop_index("ix_artist_master_id", table_name="artist_master")
    op.drop_table("artist_master")
