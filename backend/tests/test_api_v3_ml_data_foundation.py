"""API tests for V3.2 ML-ready data foundation."""

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.db.database import engine
from app.main import app

client = TestClient(app)

EXPECTED_TABLES = {
    "raw_sources",
    "raw_snapshots",
    "normalized_metrics",
    "ml_datasets",
    "ml_feature_snapshots",
    "ml_labels",
    "ml_model_runs",
    "ml_predictions",
}


def test_v3_ml_data_tables_exist_after_migration() -> None:
    """The V3.2 Alembic migration must create the full ML-ready table set."""
    table_names = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES.issubset(table_names)


def test_v3_ml_data_coverage_endpoint_lists_all_tables() -> None:
    """Coverage should expose all ML-ready tables without leaking raw payloads."""
    response = client.get("/api/v3/ml-data/coverage")
    assert response.status_code == 200
    body = response.json()
    data = body["data"]

    assert body["success"] is True
    assert data["ready"] is True
    assert {item["table_name"] for item in data["tables"]} == EXPECTED_TABLES
    assert data["totals"]["tables"] == 8
    assert data["totals"]["raw_storage_tables"] >= 2
    assert data["totals"]["training_tables"] >= 4
    assert data["totals"]["prediction_tables"] == 1
    assert data["warnings"]


def test_v3_ml_data_contracts_document_reproducibility_boundaries() -> None:
    """Contracts should separate raw storage, training inputs and predictions."""
    response = client.get("/api/v3/ml-data/contracts")
    assert response.status_code == 200
    contracts = response.json()["data"]

    by_name = {item["table_name"]: item for item in contracts}
    assert by_name["raw_snapshots"]["owns_raw_payload"] is True
    assert by_name["ml_datasets"]["versioned"] is True
    assert by_name["ml_predictions"]["expected_payload_kind"] == "prediction value, confidence and drivers"
    assert "model run" in by_name["ml_predictions"]["notes"].lower() or "frontend" in by_name["ml_predictions"]["notes"].lower()


def test_v3_ml_data_conventions_are_explicit() -> None:
    """Source, confidence and model-type values must be discoverable by API."""
    response = client.get("/api/v3/ml-data/conventions")
    assert response.status_code == 200
    data = response.json()["data"]

    assert "soundcloud" in data["source_type"]["allowed_values"]
    assert "verified" in data["confidence"]["allowed_values"]
    assert "proxy" in data["label_type"]["allowed_values"]
    assert "ml_regression" in data["model_type"]["allowed_values"]
    assert "heuristic_fallback" in data["model_type"]["allowed_values"]
