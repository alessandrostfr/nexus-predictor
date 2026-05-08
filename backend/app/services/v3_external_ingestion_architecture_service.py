"""Service for V3.4-A external collector architecture.

This macropaso creates contracts, registries and dry-run validation only. It does
not call Spotify, Last.fm, MusicBrainz, YouTube, SoundCloud, yt-dlp or scrapers.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collectors.contracts import CollectorRunStatus, CollectorStatus
from app.collectors.registry import COLLECTOR_REGISTRY, TOOL_EVALUATION_REGISTRY
from app.collectors.security import credential_status
from app.db.models import (
    ArtistMasterModel,
    CollectorRunItemModel,
    CollectorRunModel,
    NormalizedMetricModel,
    RawSnapshotModel,
    RawSourceModel,
    SourceToolEvaluationModel,
)
from app.schemas.external_ingestion_v3 import (
    V34ArchitectureResponse,
    V34ArchitectureTable,
    V34CapabilityMatrix,
    V34CollectorSourceRecord,
    V34DryRunRequest,
    V34DryRunResponse,
    V34SourceListResponse,
    V34ToolEvaluationListResponse,
    V34ToolEvaluationRecord,
)

COLLECTOR_PACKAGE_FILES = [
    "backend/app/collectors/__init__.py",
    "backend/app/collectors/base.py",
    "backend/app/collectors/contracts.py",
    "backend/app/collectors/errors.py",
    "backend/app/collectors/http_client.py",
    "backend/app/collectors/rate_limiter.py",
    "backend/app/collectors/cache.py",
    "backend/app/collectors/normalizers.py",
    "backend/app/collectors/registry.py",
    "backend/app/collectors/security.py",
    "backend/app/collectors/deduplication.py",
]


class V3ExternalIngestionArchitectureService:
    """Read/write service for source/tool registry metadata and dry-runs."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _count(self, model: type) -> int:
        """Return row count for a table model."""
        return int(self.db.scalar(select(func.count()).select_from(model)) or 0)

    def ensure_registries(self) -> dict[str, int]:
        """Upsert static source and tool registry contracts into PostgreSQL."""
        sources_upserted = 0
        tools_upserted = 0

        for contract in COLLECTOR_REGISTRY:
            existing = self.db.scalar(select(RawSourceModel).where(RawSourceModel.source_key == contract.source_key))
            payload = contract.to_source_payload()
            if existing is None:
                existing = RawSourceModel(
                    source_key=contract.source_key,
                    name=contract.source_name,
                    source_type=contract.source_type,
                    base_url=contract.base_url,
                    access_method=contract.access_method,
                    extraction_method=contract.extraction_method,
                    trust_level=contract.trust_level,
                    confidence=contract.confidence,
                    ml_value=contract.ml_value,
                    legal_risk=contract.legal_risk,
                    cost_level=contract.cost_level,
                    is_active=True,
                    requires_review=contract.requires_review,
                    notes=contract.notes,
                    raw_payload=payload,
                )
                self.db.add(existing)
            else:
                existing.name = contract.source_name
                existing.source_type = contract.source_type
                existing.base_url = contract.base_url
                existing.access_method = contract.access_method
                existing.extraction_method = contract.extraction_method
                existing.trust_level = contract.trust_level
                existing.confidence = contract.confidence
                existing.ml_value = contract.ml_value
                existing.legal_risk = contract.legal_risk
                existing.cost_level = contract.cost_level
                existing.requires_review = contract.requires_review
                existing.notes = contract.notes
                existing.raw_payload = payload
            sources_upserted += 1

        for tool in TOOL_EVALUATION_REGISTRY:
            existing = self.db.scalar(
                select(SourceToolEvaluationModel).where(
                    SourceToolEvaluationModel.tool_key == tool.tool_key,
                    SourceToolEvaluationModel.source_target == tool.source_target,
                )
            )
            if existing is None:
                existing = SourceToolEvaluationModel(
                    tool_key=tool.tool_key,
                    source_target=tool.source_target,
                    source_key=tool.source_key,
                    tool_name=tool.tool_name,
                    tool_type=tool.tool_type,
                    candidate_for=tool.candidate_for,
                    access_method=tool.access_method,
                    license_name=tool.license_name,
                    license_risk=tool.license_risk,
                    legal_risk=tool.legal_risk,
                    maintenance_status=tool.maintenance_status,
                    integration_complexity=tool.integration_complexity,
                    data_quality_expectation=tool.data_quality_expectation,
                    ml_value=tool.ml_value,
                    decision=tool.decision,
                    decision_reason=tool.decision_reason,
                    docs_url=tool.docs_url,
                    repo_url=tool.repo_url,
                    supports_cache=tool.supports_cache,
                    supports_rate_limit=tool.supports_rate_limit,
                    requires_credentials=tool.requires_credentials,
                    requires_manual_review=tool.requires_manual_review,
                    evaluation_payload=tool.evaluation_payload,
                )
                self.db.add(existing)
            else:
                existing.source_key = tool.source_key
                existing.tool_name = tool.tool_name
                existing.tool_type = tool.tool_type
                existing.candidate_for = tool.candidate_for
                existing.access_method = tool.access_method
                existing.license_name = tool.license_name
                existing.license_risk = tool.license_risk
                existing.legal_risk = tool.legal_risk
                existing.maintenance_status = tool.maintenance_status
                existing.integration_complexity = tool.integration_complexity
                existing.data_quality_expectation = tool.data_quality_expectation
                existing.ml_value = tool.ml_value
                existing.decision = tool.decision
                existing.decision_reason = tool.decision_reason
                existing.docs_url = tool.docs_url
                existing.repo_url = tool.repo_url
                existing.supports_cache = tool.supports_cache
                existing.supports_rate_limit = tool.supports_rate_limit
                existing.requires_credentials = tool.requires_credentials
                existing.requires_manual_review = tool.requires_manual_review
                existing.evaluation_payload = tool.evaluation_payload
            tools_upserted += 1

        self.db.commit()
        return {"sources_upserted": sources_upserted, "tools_upserted": tools_upserted}

    def _env_values(self, names: Iterable[str]) -> dict[str, str | None]:
        """Read environment values without exposing them in responses."""
        return {name: os.getenv(name) for name in names}

    def _contract_status(self, required_vars: tuple[str, ...], can_run_without_credentials: bool) -> tuple[str, dict[str, str]]:
        """Return configured/not_configured status for a contract."""
        if not required_vars:
            return "configured", {}
        status_by_var = credential_status(self._env_values(required_vars), required_vars)
        all_configured = all(status == "configured" for status in status_by_var.values())
        if all_configured or can_run_without_credentials:
            return "configured", status_by_var
        return "not_configured", status_by_var

    def list_sources(self) -> V34SourceListResponse:
        """Return sanitized collector/source contracts."""
        self.ensure_registries()
        records: list[V34CollectorSourceRecord] = []
        for contract in COLLECTOR_REGISTRY:
            configured_status, status_by_var = self._contract_status(contract.credential_env_vars, contract.can_run_without_credentials)
            records.append(
                V34CollectorSourceRecord(
                    source_key=contract.source_key,
                    collector_key=contract.collector_key,
                    source_name=contract.source_name,
                    source_type=contract.source_type,
                    access_method=contract.access_method,
                    extraction_method=contract.extraction_method,
                    requires_credentials=contract.requires_credentials,
                    credential_env_vars=list(contract.credential_env_vars),
                    credential_status=status_by_var,
                    rate_limit_policy=contract.rate_limit_policy.to_payload(),
                    cache_policy=contract.cache_policy.to_payload(),
                    legal_risk=contract.legal_risk,
                    ml_value=contract.ml_value,
                    cost_level=contract.cost_level,
                    trust_level=contract.trust_level,
                    confidence=contract.confidence,
                    supported_entities=list(contract.supported_entities),
                    can_run_without_credentials=contract.can_run_without_credentials,
                    collector_version=contract.collector_version,
                    normalizer_version=contract.normalizer_version,
                    schema_version=contract.schema_version,
                    capabilities=V34CapabilityMatrix(**contract.capabilities.to_payload()),
                    configured_status=configured_status,
                    notes=contract.notes,
                )
            )
        return V34SourceListResponse(
            total=len(records),
            configured=sum(1 for item in records if item.configured_status == "configured"),
            not_configured=sum(1 for item in records if item.configured_status != "configured"),
            sources=records,
        )

    def list_tools(self) -> V34ToolEvaluationListResponse:
        """Return static tool evaluations after ensuring they are stored."""
        self.ensure_registries()
        tools = [
            V34ToolEvaluationRecord(
                tool_key=tool.tool_key,
                source_target=tool.source_target,
                source_key=tool.source_key,
                tool_name=tool.tool_name,
                tool_type=tool.tool_type,
                candidate_for=tool.candidate_for,
                access_method=tool.access_method,
                license_name=tool.license_name,
                license_risk=tool.license_risk,
                legal_risk=tool.legal_risk,
                maintenance_status=tool.maintenance_status,
                integration_complexity=tool.integration_complexity,
                data_quality_expectation=tool.data_quality_expectation,
                ml_value=tool.ml_value,
                decision=tool.decision,
                decision_reason=tool.decision_reason,
                docs_url=tool.docs_url,
                repo_url=tool.repo_url,
                supports_cache=tool.supports_cache,
                supports_rate_limit=tool.supports_rate_limit,
                requires_credentials=tool.requires_credentials,
                requires_manual_review=tool.requires_manual_review,
                evaluation_payload=tool.evaluation_payload,
            )
            for tool in TOOL_EVALUATION_REGISTRY
        ]
        return V34ToolEvaluationListResponse(
            total=len(tools),
            evaluated_not_integrated=sum(1 for item in tools if "not_integrated" in item.decision),
            requires_manual_review=sum(1 for item in tools if item.requires_manual_review),
            tools=tools,
        )

    def architecture(self) -> V34ArchitectureResponse:
        """Return V3.4-A readiness and table coverage."""
        self.ensure_registries()
        tables = [
            V34ArchitectureTable(table_name="source_tool_evaluations", rows=self._count(SourceToolEvaluationModel), purpose="Tool/API/scraper/fallback evaluation registry.", required_for="tool_governance"),
            V34ArchitectureTable(table_name="collector_runs", rows=self._count(CollectorRunModel), purpose="External-ingestion run manifests and rollback flags.", required_for="run_reproducibility"),
            V34ArchitectureTable(table_name="collector_run_items", rows=self._count(CollectorRunItemModel), purpose="Per-artist/per-source run item statuses.", required_for="coverage_and_debugging"),
            V34ArchitectureTable(table_name="raw_sources", rows=self._count(RawSourceModel), purpose="Source registry reused from V3.2 with V3.4 contracts.", required_for="source_registry"),
            V34ArchitectureTable(table_name="raw_snapshots", rows=self._count(RawSnapshotModel), purpose="Raw external snapshots; V3.4-A extends it but does not populate external data.", required_for="raw_storage"),
            V34ArchitectureTable(table_name="normalized_metrics", rows=self._count(NormalizedMetricModel), purpose="Normalized source metrics; V3.4-A extends it but does not populate external data.", required_for="future_features"),
        ]
        warnings = []
        if self._count(RawSourceModel) < len(COLLECTOR_REGISTRY):
            warnings.append("Source registry has fewer rows than the static collector registry.")
        if self._count(SourceToolEvaluationModel) < len(TOOL_EVALUATION_REGISTRY):
            warnings.append("Tool evaluation registry has fewer rows than the static tool registry.")
        return V34ArchitectureResponse(
            ready=not warnings,
            collector_package=COLLECTOR_PACKAGE_FILES,
            statuses=[status.value for status in CollectorStatus],
            run_statuses=[status.value for status in CollectorRunStatus],
            tables=tables,
            warnings=warnings,
        )

    def count_2026_artists(self) -> int:
        """Return the current canonical 2026 artist count."""
        return int(
            self.db.scalar(
                select(func.count()).select_from(ArtistMasterModel).where(ArtistMasterModel.is_2026_artist.is_(True))
            )
            or 0
        )

    def dry_run(self, request: V34DryRunRequest) -> V34DryRunResponse:
        """Validate scope/sources without persisting raw snapshots or metrics."""
        source_response = self.list_sources()
        allowed_sources = {item.source_key for item in source_response.sources}
        selected_sources = request.sources or [item.source_key for item in source_response.sources]
        blocked_sources = sorted(source for source in selected_sources if source not in allowed_sources)
        selected_sources = [source for source in selected_sources if source in allowed_sources]

        artist_count = self.count_2026_artists()
        selected_artist_count = min(artist_count, request.limit or artist_count) if artist_count else 0
        configured_sources = [item.source_key for item in source_response.sources if item.source_key in selected_sources and item.configured_status == "configured"]
        not_configured_sources = [item.source_key for item in source_response.sources if item.source_key in selected_sources and item.configured_status != "configured"]
        warnings: list[str] = []
        if artist_count == 0:
            warnings.append("artist_master has no is_2026_artist=true rows. Rebuild V3.3 identity before real ingestion.")
        if blocked_sources:
            warnings.append("Some requested sources are not in the collector registry.")
        if not_configured_sources:
            warnings.append("Some selected sources are missing credentials or access confirmation.")

        manifest = {
            "artist_scope": request.artist_scope,
            "artist_count": artist_count,
            "selected_artist_count": selected_artist_count,
            "sources": selected_sources,
            "dry_run": True,
            "limit": request.limit,
            "collector_versions": {contract.source_key: contract.collector_version for contract in COLLECTOR_REGISTRY},
            "normalizer_versions": {contract.source_key: contract.normalizer_version for contract in COLLECTOR_REGISTRY},
            "metric_schema_version": "v3.4",
            "started_by": request.started_by,
            "env_status": {item.source_key: item.credential_status for item in source_response.sources if item.source_key in selected_sources},
            "quota_policy": {contract.source_key: contract.rate_limit_policy.to_payload() for contract in COLLECTOR_REGISTRY if contract.source_key in selected_sources},
            "cache_policy": {contract.source_key: contract.cache_policy.to_payload() for contract in COLLECTOR_REGISTRY if contract.source_key in selected_sources},
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        return V34DryRunResponse(
            artist_scope=request.artist_scope,
            artist_count=artist_count,
            selected_artist_count=selected_artist_count,
            selected_sources=selected_sources,
            configured_sources=configured_sources,
            not_configured_sources=not_configured_sources,
            blocked_sources=blocked_sources,
            warnings=warnings,
            manifest=manifest,
        )
