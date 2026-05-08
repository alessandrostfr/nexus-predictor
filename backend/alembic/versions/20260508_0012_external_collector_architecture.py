"""Add V3.4-A external collector architecture.

Revision ID: 20260508_0012
Revises: 20260508_0011
Create Date: 2026-05-08

V3.4-A creates collector/tool registries and run manifests. It also extends the
V3.2 raw snapshot/metric tables with canonical artist keys, source reported
timestamps and version fields needed for idempotent external ingestion.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260508_0012"
down_revision = "20260508_0011"
branch_labels = None
depends_on = None

JSON_OBJECT_DEFAULT = sa.text("'{}'::jsonb")
JSON_ARRAY_DEFAULT = sa.text("'[]'::jsonb")


def upgrade() -> None:
    """Create collector registries and run tracking tables."""
    op.create_table(
        "source_tool_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("tool_key", sa.String(length=160), nullable=False),
        sa.Column("source_target", sa.String(length=160), nullable=False),
        sa.Column("source_key", sa.String(length=160), nullable=True),
        sa.Column("tool_name", sa.String(length=255), nullable=False),
        sa.Column("tool_type", sa.String(length=80), nullable=False),
        sa.Column("candidate_for", sa.String(length=160), nullable=False),
        sa.Column("access_method", sa.String(length=80), nullable=False),
        sa.Column("license_name", sa.String(length=160), nullable=True),
        sa.Column("license_risk", sa.String(length=60), nullable=False, server_default="unknown"),
        sa.Column("legal_risk", sa.String(length=60), nullable=False, server_default="unknown"),
        sa.Column("maintenance_status", sa.String(length=80), nullable=False, server_default="unknown"),
        sa.Column("integration_complexity", sa.String(length=60), nullable=False, server_default="medium"),
        sa.Column("data_quality_expectation", sa.String(length=80), nullable=False, server_default="medium"),
        sa.Column("ml_value", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("decision", sa.String(length=100), nullable=False, server_default="spike_required"),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("docs_url", sa.Text(), nullable=True),
        sa.Column("repo_url", sa.Text(), nullable=True),
        sa.Column("supports_cache", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("supports_rate_limit", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("requires_credentials", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evaluation_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("tool_key", "source_target", name="uq_source_tool_evaluation_identity"),
    )
    op.create_index("ix_source_tool_evaluations_id", "source_tool_evaluations", ["id"], unique=False)
    op.create_index("ix_source_tool_evaluations_source_target", "source_tool_evaluations", ["source_target", "decision"], unique=False)
    op.create_index("ix_source_tool_evaluations_tool_target", "source_tool_evaluations", ["tool_key", "source_target"], unique=False)
    op.create_index("ix_source_tool_evaluations_license_risk", "source_tool_evaluations", ["license_risk", "legal_risk"], unique=False)
    op.create_index("ix_source_tool_evaluations_candidate", "source_tool_evaluations", ["candidate_for", "tool_type"], unique=False)

    op.create_table(
        "collector_runs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("run_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="running"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active_for_features", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("artist_scope", sa.String(length=120), nullable=False, server_default="nexus_2026"),
        sa.Column("artist_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_keys_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_ARRAY_DEFAULT),
        sa.Column("manifest_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("warning_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_ARRAY_DEFAULT),
        sa.Column("started_by", sa.String(length=120), nullable=False, server_default="system"),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("safe_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("run_key", name="uq_collector_runs_run_key"),
    )
    op.create_index("ix_collector_runs_id", "collector_runs", ["id"], unique=False)
    op.create_index("ix_collector_runs_status", "collector_runs", ["status", "is_active_for_features"], unique=False)
    op.create_index("ix_collector_runs_scope_started", "collector_runs", ["artist_scope", "started_at"], unique=False)

    op.create_table(
        "collector_run_items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("collector_run_id", sa.Integer(), sa.ForeignKey("collector_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canonical_artist_key", sa.String(length=255), nullable=False),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("collector_key", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="skipped"),
        sa.Column("raw_snapshot_id", sa.Integer(), sa.ForeignKey("raw_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("normalized_metric_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("profile_candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feature_candidate_metric_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(length=120), nullable=True),
        sa.Column("safe_error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quota_cost_estimated", sa.Float(), nullable=True),
        sa.Column("item_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_collector_run_items_id", "collector_run_items", ["id"], unique=False)
    op.create_index("ix_collector_run_items_collector_run_id", "collector_run_items", ["collector_run_id"], unique=False)
    op.create_index("ix_collector_run_items_raw_snapshot_id", "collector_run_items", ["raw_snapshot_id"], unique=False)
    op.create_index("ix_collector_run_items_run_artist_source", "collector_run_items", ["collector_run_id", "canonical_artist_key", "source_key"], unique=False)
    op.create_index("ix_collector_run_items_artist_source", "collector_run_items", ["canonical_artist_key", "source_key"], unique=False)
    op.create_index("ix_collector_run_items_status", "collector_run_items", ["status", "source_key"], unique=False)

    op.add_column("raw_snapshots", sa.Column("canonical_artist_key", sa.String(length=255), nullable=True))
    op.add_column("raw_snapshots", sa.Column("collector_run_id", sa.Integer(), nullable=True))
    op.add_column("raw_snapshots", sa.Column("collector_key", sa.String(length=160), nullable=True))
    op.add_column("raw_snapshots", sa.Column("source_reported_at", sa.DateTime(), nullable=True))
    op.add_column("raw_snapshots", sa.Column("collector_version", sa.String(length=80), nullable=True))
    op.add_column("raw_snapshots", sa.Column("normalizer_version", sa.String(length=80), nullable=True))
    op.create_foreign_key("fk_raw_snapshots_collector_run_id", "raw_snapshots", "collector_runs", ["collector_run_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_raw_snapshots_collector_run_id", "raw_snapshots", ["collector_run_id"], unique=False)
    op.create_index("ix_raw_snapshots_artist_source", "raw_snapshots", ["canonical_artist_key", "source_key"], unique=False)

    op.add_column("normalized_metrics", sa.Column("canonical_artist_key", sa.String(length=255), nullable=True))
    op.add_column("normalized_metrics", sa.Column("collector_run_id", sa.Integer(), nullable=True))
    op.add_column("normalized_metrics", sa.Column("collector_key", sa.String(length=160), nullable=True))
    op.add_column("normalized_metrics", sa.Column("source_reported_at", sa.DateTime(), nullable=True))
    op.add_column("normalized_metrics", sa.Column("collector_version", sa.String(length=80), nullable=True))
    op.add_column("normalized_metrics", sa.Column("normalizer_version", sa.String(length=80), nullable=True))
    op.add_column("normalized_metrics", sa.Column("metric_schema_version", sa.String(length=80), nullable=False, server_default="v3.4"))
    op.add_column("normalized_metrics", sa.Column("is_diagnostic_only", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_foreign_key("fk_normalized_metrics_collector_run_id", "normalized_metrics", "collector_runs", ["collector_run_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_normalized_metrics_collector_run_id", "normalized_metrics", ["collector_run_id"], unique=False)
    op.create_index("ix_normalized_metrics_artist_metric", "normalized_metrics", ["canonical_artist_key", "metric_key"], unique=False)


def downgrade() -> None:
    """Drop V3.4-A collector architecture objects."""
    op.drop_index("ix_normalized_metrics_artist_metric", table_name="normalized_metrics")
    op.drop_index("ix_normalized_metrics_collector_run_id", table_name="normalized_metrics")
    op.drop_constraint("fk_normalized_metrics_collector_run_id", "normalized_metrics", type_="foreignkey")
    op.drop_column("normalized_metrics", "is_diagnostic_only")
    op.drop_column("normalized_metrics", "metric_schema_version")
    op.drop_column("normalized_metrics", "normalizer_version")
    op.drop_column("normalized_metrics", "collector_version")
    op.drop_column("normalized_metrics", "source_reported_at")
    op.drop_column("normalized_metrics", "collector_key")
    op.drop_column("normalized_metrics", "collector_run_id")
    op.drop_column("normalized_metrics", "canonical_artist_key")

    op.drop_index("ix_raw_snapshots_artist_source", table_name="raw_snapshots")
    op.drop_index("ix_raw_snapshots_collector_run_id", table_name="raw_snapshots")
    op.drop_constraint("fk_raw_snapshots_collector_run_id", "raw_snapshots", type_="foreignkey")
    op.drop_column("raw_snapshots", "normalizer_version")
    op.drop_column("raw_snapshots", "collector_version")
    op.drop_column("raw_snapshots", "source_reported_at")
    op.drop_column("raw_snapshots", "collector_key")
    op.drop_column("raw_snapshots", "collector_run_id")
    op.drop_column("raw_snapshots", "canonical_artist_key")

    op.drop_index("ix_collector_run_items_status", table_name="collector_run_items")
    op.drop_index("ix_collector_run_items_artist_source", table_name="collector_run_items")
    op.drop_index("ix_collector_run_items_run_artist_source", table_name="collector_run_items")
    op.drop_index("ix_collector_run_items_raw_snapshot_id", table_name="collector_run_items")
    op.drop_index("ix_collector_run_items_collector_run_id", table_name="collector_run_items")
    op.drop_index("ix_collector_run_items_id", table_name="collector_run_items")
    op.drop_table("collector_run_items")

    op.drop_index("ix_collector_runs_scope_started", table_name="collector_runs")
    op.drop_index("ix_collector_runs_status", table_name="collector_runs")
    op.drop_index("ix_collector_runs_id", table_name="collector_runs")
    op.drop_table("collector_runs")

    op.drop_index("ix_source_tool_evaluations_candidate", table_name="source_tool_evaluations")
    op.drop_index("ix_source_tool_evaluations_license_risk", table_name="source_tool_evaluations")
    op.drop_index("ix_source_tool_evaluations_tool_target", table_name="source_tool_evaluations")
    op.drop_index("ix_source_tool_evaluations_source_target", table_name="source_tool_evaluations")
    op.drop_index("ix_source_tool_evaluations_id", table_name="source_tool_evaluations")
    op.drop_table("source_tool_evaluations")
