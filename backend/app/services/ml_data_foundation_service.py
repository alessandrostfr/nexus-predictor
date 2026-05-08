"""Service for V3.2 ML-ready data foundation inspection.

V3.2 does not train models. Its job is to make future model training auditable:
we can store raw snapshots, normalized metrics, versioned datasets, feature
vectors, labels/proxies, model runs and predictions separately.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    MLDatasetModel,
    MLFeatureSnapshotModel,
    MLLabelModel,
    MLModelRunModel,
    MLPredictionModel,
    NormalizedMetricModel,
    RawSnapshotModel,
    RawSourceModel,
)
from app.schemas.ml_data import (
    MLDataConvention,
    MLDataConventionsResponse,
    MLDataCoverageResponse,
    MLDataTableContract,
    MLDataTableCoverage,
)


@dataclass(frozen=True)
class TableDefinition:
    """Internal table contract used by coverage and documentation endpoints."""

    table_name: str
    model: type
    purpose: str
    required_for: str
    stores_raw_payload: bool = False
    stores_training_data: bool = False
    stores_predictions: bool = False
    versioned: bool = False
    expected_payload_kind: str = "metadata"
    notes: str = ""


TABLE_DEFINITIONS: tuple[TableDefinition, ...] = (
    TableDefinition(
        table_name="raw_sources",
        model=RawSourceModel,
        purpose="Registry of source systems used by V3 ingestion.",
        required_for="ingestion_governance",
        stores_raw_payload=True,
        versioned=False,
        expected_payload_kind="source metadata and policy metadata",
        notes="Complements the V2 evidence sources table with ML-ingestion metadata such as risk, cost and ML value.",
    ),
    TableDefinition(
        table_name="raw_snapshots",
        model=RawSnapshotModel,
        purpose="Immutable-ish captured payloads from APIs, tools, scrapers or manual imports.",
        required_for="raw_storage_and_reprocessing",
        stores_raw_payload=True,
        versioned=True,
        expected_payload_kind="original API/scraper/manual payload",
        notes="This is the audit trail for future normalization and feature regeneration.",
    ),
    TableDefinition(
        table_name="normalized_metrics",
        model=NormalizedMetricModel,
        purpose="Source-specific metrics converted into common numeric/text fields.",
        required_for="feature_engineering",
        stores_raw_payload=True,
        versioned=False,
        expected_payload_kind="metric provenance and normalization metadata",
        notes="Metrics here are feature candidates, not predictions.",
    ),
    TableDefinition(
        table_name="ml_datasets",
        model=MLDatasetModel,
        purpose="Versioned dataset manifests for training, evaluation and prediction.",
        required_for="training_reproducibility",
        stores_training_data=True,
        versioned=True,
        expected_payload_kind="feature/label schema and lineage metadata",
        notes="A model run must point back to the dataset version it used.",
    ),
    TableDefinition(
        table_name="ml_feature_snapshots",
        model=MLFeatureSnapshotModel,
        purpose="Feature vectors by entity and dataset version.",
        required_for="model_training_inputs",
        stores_training_data=True,
        versioned=True,
        expected_payload_kind="feature vector JSON",
        notes="Feature snapshots make it possible to inspect exactly what the model saw.",
    ),
    TableDefinition(
        table_name="ml_labels",
        model=MLLabelModel,
        purpose="Targets and proxies used by supervised training.",
        required_for="supervised_learning",
        stores_training_data=True,
        versioned=True,
        expected_payload_kind="target/proxy evidence payload",
        notes="Labels must identify whether they are confirmed, inferred or proxy.",
    ),
    TableDefinition(
        table_name="ml_model_runs",
        model=MLModelRunModel,
        purpose="Training/evaluation metadata for baselines and real ML models.",
        required_for="model_registry",
        stores_training_data=True,
        versioned=True,
        expected_payload_kind="metrics, parameters and artifact references",
        notes="Future real ML blocks must store fit/evaluation metadata here.",
    ),
    TableDefinition(
        table_name="ml_predictions",
        model=MLPredictionModel,
        purpose="Persisted model outputs consumed by API/frontend.",
        required_for="prediction_serving",
        stores_predictions=True,
        versioned=True,
        expected_payload_kind="prediction value, confidence and drivers",
        notes="Frontend must consume this table via APIs instead of fake constants once ML blocks are active.",
    ),
)


class MLDataFoundationService:
    """Read-only service for V3.2 ML data foundation checks."""

    def __init__(self, db: Session) -> None:
        """Store the request-scoped database session."""
        self.db = db

    def coverage(self) -> MLDataCoverageResponse:
        """Return row counts and readiness for the V3.2 tables."""
        table_payloads: list[MLDataTableCoverage] = []
        totals = {
            "tables": len(TABLE_DEFINITIONS),
            "rows": 0,
            "raw_storage_tables": 0,
            "training_tables": 0,
            "prediction_tables": 0,
        }

        for definition in TABLE_DEFINITIONS:
            rows = int(self.db.scalar(select(func.count()).select_from(definition.model)) or 0)
            totals["rows"] += rows
            totals["raw_storage_tables"] += int(definition.stores_raw_payload)
            totals["training_tables"] += int(definition.stores_training_data)
            totals["prediction_tables"] += int(definition.stores_predictions)
            table_payloads.append(
                MLDataTableCoverage(
                    table_name=definition.table_name,
                    rows=rows,
                    purpose=definition.purpose,
                    required_for=definition.required_for,
                    stores_raw_payload=definition.stores_raw_payload,
                    stores_training_data=definition.stores_training_data,
                    stores_predictions=definition.stores_predictions,
                )
            )

        return MLDataCoverageResponse(
            ready=True,
            tables=table_payloads,
            totals=totals,
            warnings=[
                "V3.2 only creates the ML-ready storage foundation; datasets, labels and predictions will be populated in later blocks.",
                "Empty row counts are expected immediately after the migration.",
            ],
        )

    def table_contracts(self) -> list[MLDataTableContract]:
        """Return static table contracts for docs/debugging."""
        return [
            MLDataTableContract(
                table_name=definition.table_name,
                purpose=definition.purpose,
                owns_raw_payload=definition.stores_raw_payload,
                versioned=definition.versioned,
                expected_payload_kind=definition.expected_payload_kind,
                notes=definition.notes,
            )
            for definition in TABLE_DEFINITIONS
        ]

    def conventions(self) -> MLDataConventionsResponse:
        """Return value conventions that future ingestion/training blocks must reuse."""
        return MLDataConventionsResponse(
            source_type=MLDataConvention(
                key="source_type",
                allowed_values=["spotify", "soundcloud", "youtube", "lastfm", "musicbrainz", "social", "events", "venue", "manual", "internal", "web"],
                description="Where a raw source or snapshot comes from. Add new values only with docs and tests.",
            ),
            confidence=MLDataConvention(
                key="confidence",
                allowed_values=["verified", "high", "medium", "low", "rejected", "unknown"],
                description="Trust level for sources, snapshots, metrics, labels and predictions.",
            ),
            extraction_method=MLDataConvention(
                key="extraction_method",
                allowed_values=["api", "official_api", "open_source_tool", "httpx_bs4", "playwright", "manual_review", "csv_import", "internal_seed", "unknown"],
                description="How a payload was acquired. Scraping/tooling choices must be justified in docs.",
            ),
            dataset_kind=MLDataConvention(
                key="dataset_kind",
                allowed_values=["training", "validation", "test", "prediction", "debug", "baseline"],
                description="What a dataset version is used for.",
            ),
            label_type=MLDataConvention(
                key="label_type",
                allowed_values=["confirmed", "inferred", "proxy", "manual_evidence", "rejected"],
                description="Whether a target is direct truth or a documented proxy.",
            ),
            model_type=MLDataConvention(
                key="model_type",
                allowed_values=["baseline", "ml_regression", "ml_classification", "ml_ordinal", "optimizer", "heuristic_fallback"],
                description="Only trained model types with fit/evaluation can be presented as ML.",
            ),
            prediction_status=MLDataConvention(
                key="prediction_status",
                allowed_values=["draft", "candidate", "validated", "final", "stale", "rejected"],
                description="Serving state for persisted model outputs.",
            ),
        )
