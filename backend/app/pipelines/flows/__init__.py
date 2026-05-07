"""Prefect flow definitions for V2 ingestion and processing."""

from app.pipelines.flows.external_ingestion_flow import external_ingestion_flow

__all__ = ["external_ingestion_flow"]
