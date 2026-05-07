"""Add V2 evidence layer tables.

Revision ID: 20260507_0002
Revises: 20260507_0001
Create Date: 2026-05-07

This migration creates the data model required by V2.1: sources, atomic
evidence, derived artist metrics, platform/social profiles, career events and
venue/festival prestige. It intentionally does not change the V1-compatible
endpoint tables so the current API remains stable during the V2 transition.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260507_0002"
down_revision = "20260507_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create V2 evidence and source registry tables."""
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("default_confidence", sa.String(length=40), nullable=False),
        sa.Column("extraction_method", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("key", name="uq_sources_key"),
    )
    op.create_index("ix_sources_id", "sources", ["id"], unique=False)
    op.create_index("ix_sources_type_confidence", "sources", ["source_type", "default_confidence"], unique=False)

    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="CASCADE"), nullable=True),
        sa.Column("artist_slug", sa.String(length=255), nullable=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("metric_key", sa.String(length=160), nullable=False),
        sa.Column("metric_value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.String(length=40), nullable=False),
        sa.Column("extraction_method", sa.String(length=80), nullable=False),
        sa.Column("evidence_kind", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_evidence_items_id", "evidence_items", ["id"], unique=False)
    op.create_index("ix_evidence_items_artist_id", "evidence_items", ["artist_id"], unique=False)
    op.create_index("ix_evidence_items_artist_slug", "evidence_items", ["artist_slug"], unique=False)
    op.create_index("ix_evidence_items_metric_key", "evidence_items", ["metric_key"], unique=False)
    op.create_index("ix_evidence_items_source_id", "evidence_items", ["source_id"], unique=False)
    op.create_index("ix_evidence_artist_metric", "evidence_items", ["artist_slug", "metric_key"], unique=False)
    op.create_index("ix_evidence_source_confidence", "evidence_items", ["source_type", "confidence"], unique=False)
    op.create_index("ix_evidence_status", "evidence_items", ["status"], unique=False)

    op.create_table(
        "artist_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="CASCADE"), nullable=True),
        sa.Column("artist_slug", sa.String(length=255), nullable=False),
        sa.Column("metric_key", sa.String(length=160), nullable=False),
        sa.Column("metric_value_numeric", sa.Float(), nullable=True),
        sa.Column("metric_value_text", sa.Text(), nullable=True),
        sa.Column("value_type", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.String(length=40), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("latest_captured_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("artist_slug", "metric_key", name="uq_artist_metrics_artist_metric"),
    )
    op.create_index("ix_artist_metrics_id", "artist_metrics", ["id"], unique=False)
    op.create_index("ix_artist_metrics_artist_id", "artist_metrics", ["artist_id"], unique=False)
    op.create_index("ix_artist_metrics_artist_slug", "artist_metrics", ["artist_slug"], unique=False)
    op.create_index("ix_artist_metrics_metric_confidence", "artist_metrics", ["metric_key", "confidence"], unique=False)

    op.create_table(
        "platform_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="CASCADE"), nullable=True),
        sa.Column("artist_slug", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=80), nullable=False),
        sa.Column("profile_name", sa.String(length=255), nullable=True),
        sa.Column("profile_url", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("is_official", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.String(length=40), nullable=False),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("artist_slug", "platform", "profile_url", name="uq_platform_profile_url"),
    )
    op.create_index("ix_platform_profiles_id", "platform_profiles", ["id"], unique=False)
    op.create_index("ix_platform_profiles_artist_slug", "platform_profiles", ["artist_slug"], unique=False)
    op.create_index("ix_platform_profiles_platform", "platform_profiles", ["platform"], unique=False)

    op.create_table(
        "social_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="CASCADE"), nullable=True),
        sa.Column("artist_slug", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=80), nullable=False),
        sa.Column("handle", sa.String(length=255), nullable=True),
        sa.Column("profile_url", sa.Text(), nullable=True),
        sa.Column("follower_count", sa.Integer(), nullable=True),
        sa.Column("engagement_rate", sa.Float(), nullable=True),
        sa.Column("average_views", sa.Integer(), nullable=True),
        sa.Column("last_post_at", sa.DateTime(), nullable=True),
        sa.Column("is_official", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.String(length=40), nullable=False),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("artist_slug", "platform", "profile_url", name="uq_social_profile_url"),
    )
    op.create_index("ix_social_profiles_id", "social_profiles", ["id"], unique=False)
    op.create_index("ix_social_profiles_artist_slug", "social_profiles", ["artist_slug"], unique=False)
    op.create_index("ix_social_profiles_platform", "social_profiles", ["platform"], unique=False)

    op.create_table(
        "career_events",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="CASCADE"), nullable=True),
        sa.Column("artist_slug", sa.String(length=255), nullable=False),
        sa.Column("event_name", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("role", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("venue_name", sa.String(length=255), nullable=True),
        sa.Column("event_date", sa.String(length=50), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("is_headliner", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_career_events_id", "career_events", ["id"], unique=False)
    op.create_index("ix_career_events_artist_slug", "career_events", ["artist_slug"], unique=False)
    op.create_index("ix_career_events_artist_year", "career_events", ["artist_slug", "year"], unique=False)
    op.create_index("ix_career_events_event_type", "career_events", ["event_type"], unique=False)

    op.create_table(
        "venue_prestige",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("venue_type", sa.String(length=80), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("prestige_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_venue_prestige_slug"),
    )
    op.create_index("ix_venue_prestige_id", "venue_prestige", ["id"], unique=False)
    op.create_index("ix_venue_prestige_type_score", "venue_prestige", ["venue_type", "prestige_score"], unique=False)


def downgrade() -> None:
    """Drop V2 evidence tables in dependency-safe order."""
    op.drop_index("ix_venue_prestige_type_score", table_name="venue_prestige")
    op.drop_index("ix_venue_prestige_id", table_name="venue_prestige")
    op.drop_table("venue_prestige")

    op.drop_index("ix_career_events_event_type", table_name="career_events")
    op.drop_index("ix_career_events_artist_year", table_name="career_events")
    op.drop_index("ix_career_events_artist_slug", table_name="career_events")
    op.drop_index("ix_career_events_id", table_name="career_events")
    op.drop_table("career_events")

    op.drop_index("ix_social_profiles_platform", table_name="social_profiles")
    op.drop_index("ix_social_profiles_artist_slug", table_name="social_profiles")
    op.drop_index("ix_social_profiles_id", table_name="social_profiles")
    op.drop_table("social_profiles")

    op.drop_index("ix_platform_profiles_platform", table_name="platform_profiles")
    op.drop_index("ix_platform_profiles_artist_slug", table_name="platform_profiles")
    op.drop_index("ix_platform_profiles_id", table_name="platform_profiles")
    op.drop_table("platform_profiles")

    op.drop_index("ix_artist_metrics_metric_confidence", table_name="artist_metrics")
    op.drop_index("ix_artist_metrics_artist_slug", table_name="artist_metrics")
    op.drop_index("ix_artist_metrics_artist_id", table_name="artist_metrics")
    op.drop_index("ix_artist_metrics_id", table_name="artist_metrics")
    op.drop_table("artist_metrics")

    op.drop_index("ix_evidence_status", table_name="evidence_items")
    op.drop_index("ix_evidence_source_confidence", table_name="evidence_items")
    op.drop_index("ix_evidence_artist_metric", table_name="evidence_items")
    op.drop_index("ix_evidence_items_source_id", table_name="evidence_items")
    op.drop_index("ix_evidence_items_metric_key", table_name="evidence_items")
    op.drop_index("ix_evidence_items_artist_slug", table_name="evidence_items")
    op.drop_index("ix_evidence_items_artist_id", table_name="evidence_items")
    op.drop_index("ix_evidence_items_id", table_name="evidence_items")
    op.drop_table("evidence_items")

    op.drop_index("ix_sources_type_confidence", table_name="sources")
    op.drop_index("ix_sources_id", table_name="sources")
    op.drop_table("sources")
