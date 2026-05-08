"""Schemas for the V3.2 ML-ready data foundation.

These schemas are debug/inspection contracts. They intentionally expose table
purpose, row counts and conventions without returning raw payloads or secrets.
"""

from pydantic import BaseModel, Field


class MLDataTableCoverage(BaseModel):
    """Coverage summary for one V3.2 ML data table."""

    table_name: str
    rows: int
    purpose: str
    required_for: str
    stores_raw_payload: bool = False
    stores_training_data: bool = False
    stores_predictions: bool = False


class MLDataCoverageResponse(BaseModel):
    """High-level coverage payload returned by /api/v3/ml-data/coverage."""

    block: str = "V3.2"
    ready: bool
    tables: list[MLDataTableCoverage]
    totals: dict[str, int]
    warnings: list[str] = Field(default_factory=list)


class MLDataTableContract(BaseModel):
    """Static table contract used to document the ML data foundation."""

    table_name: str
    purpose: str
    owns_raw_payload: bool
    versioned: bool
    expected_payload_kind: str
    notes: str


class MLDataConvention(BaseModel):
    """Naming convention for source types, confidence values and ML statuses."""

    key: str
    allowed_values: list[str]
    description: str


class MLDataConventionsResponse(BaseModel):
    """V3.2 conventions for future ingestion and ML blocks."""

    source_type: MLDataConvention
    confidence: MLDataConvention
    extraction_method: MLDataConvention
    dataset_kind: MLDataConvention
    label_type: MLDataConvention
    model_type: MLDataConvention
    prediction_status: MLDataConvention
