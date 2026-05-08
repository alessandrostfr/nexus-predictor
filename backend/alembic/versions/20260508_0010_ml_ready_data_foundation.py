"""Add V3.2 ML-ready data foundation.

Revision ID: 20260508_0010
Revises: 20260508_0009
Create Date: 2026-05-08

V3.2 creates the storage layer that makes future ML reproducible: raw source
registry, raw snapshots, normalized metrics, versioned datasets, feature
snapshots, labels/proxies, model runs and persisted predictions.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260508_0010"
down_revision = "20260508_0009"
branch_labels = None
depends_on = None

JSON_OBJECT_DEFAULT = sa.text("'{}'::jsonb")
JSON_ARRAY_DEFAULT = sa.text("'[]'::jsonb")


def upgrade() -> None:
    """Create V3.2 ML-ready data tables."""
    op.create_table(
        "raw_sources",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("access_method", sa.String(length=80), nullable=False, server_default="unknown"),
        sa.Column("extraction_method", sa.String(length=80), nullable=False, server_default="manual"),
        sa.Column("trust_level", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("ml_value", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("legal_risk", sa.String(length=40), nullable=False, server_default="unknown"),
        sa.Column("cost_level", sa.String(length=40), nullable=False, server_default="free_or_unknown"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("source_key", name="uq_raw_sources_source_key"),
    )
    op.create_index("ix_raw_sources_id", "raw_sources", ["id"], unique=False)
    op.create_index("ix_raw_sources_type_confidence", "raw_sources", ["source_type", "confidence"], unique=False)
    op.create_index("ix_raw_sources_active_ml_value", "raw_sources", ["is_active", "ml_value"], unique=False)

    op.create_table(
        "raw_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("raw_source_id", sa.Integer(), sa.ForeignKey("raw_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("snapshot_key", sa.String(length=255), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("extraction_method", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="captured"),
        sa.Column("schema_version", sa.String(length=80), nullable=False, server_default="v3.2"),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("normalized_hint_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("snapshot_key", name="uq_raw_snapshots_snapshot_key"),
    )
    op.create_index("ix_raw_snapshots_id", "raw_snapshots", ["id"], unique=False)
    op.create_index("ix_raw_snapshots_raw_source_id", "raw_snapshots", ["raw_source_id"], unique=False)
    op.create_index("ix_raw_snapshots_entity", "raw_snapshots", ["entity_type", "entity_key"], unique=False)
    op.create_index("ix_raw_snapshots_source_captured", "raw_snapshots", ["source_key", "captured_at"], unique=False)
    op.create_index("ix_raw_snapshots_status", "raw_snapshots", ["status"], unique=False)

    op.create_table(
        "normalized_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("raw_snapshot_id", sa.Integer(), sa.ForeignKey("raw_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("metric_key", sa.String(length=160), nullable=False),
        sa.Column("metric_value_numeric", sa.Float(), nullable=True),
        sa.Column("metric_value_text", sa.Text(), nullable=True),
        sa.Column("metric_unit", sa.String(length=80), nullable=True),
        sa.Column("value_type", sa.String(length=40), nullable=False, server_default="numeric"),
        sa.Column("normalized_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("captured_at", sa.DateTime(), nullable=True),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("extraction_method", sa.String(length=80), nullable=False, server_default="unknown"),
        sa.Column("source_method", sa.String(length=80), nullable=False, server_default="normalized_from_raw"),
        sa.Column("feature_candidate", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_normalized_metrics_id", "normalized_metrics", ["id"], unique=False)
    op.create_index("ix_normalized_metrics_raw_snapshot_id", "normalized_metrics", ["raw_snapshot_id"], unique=False)
    op.create_index("ix_normalized_metrics_entity_metric", "normalized_metrics", ["entity_type", "entity_key", "metric_key"], unique=False)
    op.create_index("ix_normalized_metrics_source", "normalized_metrics", ["source_key", "confidence"], unique=False)
    op.create_index("ix_normalized_metrics_feature_candidate", "normalized_metrics", ["feature_candidate"], unique=False)

    op.create_table(
        "ml_datasets",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("dataset_key", sa.String(length=255), nullable=False),
        sa.Column("model_target", sa.String(length=120), nullable=False),
        sa.Column("dataset_version", sa.String(length=80), nullable=False),
        sa.Column("dataset_kind", sa.String(length=80), nullable=False, server_default="training"),
        sa.Column("entity_type", sa.String(length=80), nullable=False, server_default="artist"),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feature_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("label_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_year", sa.Integer(), nullable=True),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column("split_strategy", sa.String(length=120), nullable=False, server_default="not_built_yet"),
        sa.Column("source_snapshot_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="draft"),
        sa.Column("is_training_dataset", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("feature_schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("label_schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("lineage_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("dataset_key", name="uq_ml_datasets_dataset_key"),
    )
    op.create_index("ix_ml_datasets_id", "ml_datasets", ["id"], unique=False)
    op.create_index("ix_ml_datasets_target_version", "ml_datasets", ["model_target", "dataset_version"], unique=False)
    op.create_index("ix_ml_datasets_status", "ml_datasets", ["status"], unique=False)

    op.create_table(
        "ml_feature_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("dataset_id", sa.Integer(), sa.ForeignKey("ml_datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dataset_key", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("feature_set_name", sa.String(length=120), nullable=False),
        sa.Column("feature_version", sa.String(length=80), nullable=False),
        sa.Column("feature_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("feature_columns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_ARRAY_DEFAULT),
        sa.Column("missing_features_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_ARRAY_DEFAULT),
        sa.Column("source_metric_keys_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_ARRAY_DEFAULT),
        sa.Column("source_snapshot_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_ARRAY_DEFAULT),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("leakage_checked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("dataset_key", "entity_type", "entity_key", "feature_set_name", "feature_version", name="uq_ml_feature_snapshot_identity"),
    )
    op.create_index("ix_ml_feature_snapshots_id", "ml_feature_snapshots", ["id"], unique=False)
    op.create_index("ix_ml_feature_snapshots_dataset_id", "ml_feature_snapshots", ["dataset_id"], unique=False)
    op.create_index("ix_ml_feature_snapshots_dataset", "ml_feature_snapshots", ["dataset_id", "feature_set_name"], unique=False)
    op.create_index("ix_ml_feature_snapshots_entity", "ml_feature_snapshots", ["entity_type", "entity_key"], unique=False)
    op.create_index("ix_ml_feature_snapshots_status", "ml_feature_snapshots", ["status"], unique=False)

    op.create_table(
        "ml_labels",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("dataset_id", sa.Integer(), sa.ForeignKey("ml_datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("model_target", sa.String(length=120), nullable=False),
        sa.Column("label_key", sa.String(length=160), nullable=False),
        sa.Column("label_version", sa.String(length=80), nullable=False),
        sa.Column("label_value_numeric", sa.Float(), nullable=True),
        sa.Column("label_value_text", sa.Text(), nullable=True),
        sa.Column("label_value_category", sa.String(length=120), nullable=True),
        sa.Column("source_method", sa.String(length=120), nullable=False),
        sa.Column("label_type", sa.String(length=60), nullable=False, server_default="proxy"),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("evidence_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ml_labels_id", "ml_labels", ["id"], unique=False)
    op.create_index("ix_ml_labels_dataset_id", "ml_labels", ["dataset_id"], unique=False)
    op.create_index("ix_ml_labels_target_version", "ml_labels", ["model_target", "label_version"], unique=False)
    op.create_index("ix_ml_labels_entity", "ml_labels", ["entity_type", "entity_key"], unique=False)
    op.create_index("ix_ml_labels_type_confidence", "ml_labels", ["label_type", "confidence"], unique=False)

    op.create_table(
        "ml_model_runs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("run_key", sa.String(length=255), nullable=False),
        sa.Column("model_name", sa.String(length=160), nullable=False),
        sa.Column("model_target", sa.String(length=120), nullable=False),
        sa.Column("model_type", sa.String(length=80), nullable=False),
        sa.Column("algorithm", sa.String(length=120), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("dataset_id", sa.Integer(), sa.ForeignKey("ml_datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dataset_key", sa.String(length=255), nullable=True),
        sa.Column("trained", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("training_started_at", sa.DateTime(), nullable=True),
        sa.Column("training_finished_at", sa.DateTime(), nullable=True),
        sa.Column("training_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feature_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("parameters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("run_key", name="uq_ml_model_runs_run_key"),
    )
    op.create_index("ix_ml_model_runs_id", "ml_model_runs", ["id"], unique=False)
    op.create_index("ix_ml_model_runs_dataset_id", "ml_model_runs", ["dataset_id"], unique=False)
    op.create_index("ix_ml_model_runs_target_version", "ml_model_runs", ["model_target", "model_version"], unique=False)
    op.create_index("ix_ml_model_runs_status", "ml_model_runs", ["status"], unique=False)

    op.create_table(
        "ml_predictions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("model_run_id", sa.Integer(), sa.ForeignKey("ml_model_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("feature_snapshot_id", sa.Integer(), sa.ForeignKey("ml_feature_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("run_key", sa.String(length=255), nullable=False),
        sa.Column("model_target", sa.String(length=120), nullable=False),
        sa.Column("prediction_year", sa.Integer(), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("prediction_key", sa.String(length=255), nullable=False),
        sa.Column("prediction_value_numeric", sa.Float(), nullable=True),
        sa.Column("prediction_value_text", sa.Text(), nullable=True),
        sa.Column("prediction_class", sa.String(length=120), nullable=True),
        sa.Column("prediction_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_OBJECT_DEFAULT),
        sa.Column("confidence", sa.String(length=40), nullable=False, server_default="medium"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("drivers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=JSON_ARRAY_DEFAULT),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="draft"),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("run_key", "prediction_key", name="uq_ml_predictions_run_prediction"),
    )
    op.create_index("ix_ml_predictions_id", "ml_predictions", ["id"], unique=False)
    op.create_index("ix_ml_predictions_model_run_id", "ml_predictions", ["model_run_id"], unique=False)
    op.create_index("ix_ml_predictions_feature_snapshot_id", "ml_predictions", ["feature_snapshot_id"], unique=False)
    op.create_index("ix_ml_predictions_target_year", "ml_predictions", ["model_target", "prediction_year"], unique=False)
    op.create_index("ix_ml_predictions_entity", "ml_predictions", ["entity_type", "entity_key"], unique=False)
    op.create_index("ix_ml_predictions_final", "ml_predictions", ["is_final", "status"], unique=False)


def downgrade() -> None:
    """Drop V3.2 ML-ready data tables in dependency-safe order."""
    op.drop_index("ix_ml_predictions_final", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_entity", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_target_year", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_feature_snapshot_id", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_model_run_id", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_id", table_name="ml_predictions")
    op.drop_table("ml_predictions")

    op.drop_index("ix_ml_model_runs_status", table_name="ml_model_runs")
    op.drop_index("ix_ml_model_runs_target_version", table_name="ml_model_runs")
    op.drop_index("ix_ml_model_runs_dataset_id", table_name="ml_model_runs")
    op.drop_index("ix_ml_model_runs_id", table_name="ml_model_runs")
    op.drop_table("ml_model_runs")

    op.drop_index("ix_ml_labels_type_confidence", table_name="ml_labels")
    op.drop_index("ix_ml_labels_entity", table_name="ml_labels")
    op.drop_index("ix_ml_labels_target_version", table_name="ml_labels")
    op.drop_index("ix_ml_labels_dataset_id", table_name="ml_labels")
    op.drop_index("ix_ml_labels_id", table_name="ml_labels")
    op.drop_table("ml_labels")

    op.drop_index("ix_ml_feature_snapshots_status", table_name="ml_feature_snapshots")
    op.drop_index("ix_ml_feature_snapshots_entity", table_name="ml_feature_snapshots")
    op.drop_index("ix_ml_feature_snapshots_dataset", table_name="ml_feature_snapshots")
    op.drop_index("ix_ml_feature_snapshots_dataset_id", table_name="ml_feature_snapshots")
    op.drop_index("ix_ml_feature_snapshots_id", table_name="ml_feature_snapshots")
    op.drop_table("ml_feature_snapshots")

    op.drop_index("ix_ml_datasets_status", table_name="ml_datasets")
    op.drop_index("ix_ml_datasets_target_version", table_name="ml_datasets")
    op.drop_index("ix_ml_datasets_id", table_name="ml_datasets")
    op.drop_table("ml_datasets")

    op.drop_index("ix_normalized_metrics_feature_candidate", table_name="normalized_metrics")
    op.drop_index("ix_normalized_metrics_source", table_name="normalized_metrics")
    op.drop_index("ix_normalized_metrics_entity_metric", table_name="normalized_metrics")
    op.drop_index("ix_normalized_metrics_raw_snapshot_id", table_name="normalized_metrics")
    op.drop_index("ix_normalized_metrics_id", table_name="normalized_metrics")
    op.drop_table("normalized_metrics")

    op.drop_index("ix_raw_snapshots_status", table_name="raw_snapshots")
    op.drop_index("ix_raw_snapshots_source_captured", table_name="raw_snapshots")
    op.drop_index("ix_raw_snapshots_entity", table_name="raw_snapshots")
    op.drop_index("ix_raw_snapshots_raw_source_id", table_name="raw_snapshots")
    op.drop_index("ix_raw_snapshots_id", table_name="raw_snapshots")
    op.drop_table("raw_snapshots")

    op.drop_index("ix_raw_sources_active_ml_value", table_name="raw_sources")
    op.drop_index("ix_raw_sources_type_confidence", table_name="raw_sources")
    op.drop_index("ix_raw_sources_id", table_name="raw_sources")
    op.drop_table("raw_sources")
