"""V3.4-B official API credential diagnostics and probe orchestration.

This service separates offline diagnostics from real external calls. Tests can
exercise credentials and dry probe planning without internet, while scripts and
manual endpoint checks may explicitly set ``execute_real_calls=true``.
"""

from __future__ import annotations

import time
from datetime import timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collectors.contracts import CollectorRunStatus, CollectorStatus
from app.collectors.deduplication import build_snapshot_key, content_hash, utc_now
from app.collectors.official_apis import (
    ArtistProbeTarget,
    OfficialProbeResult,
    official_collector_for_source,
    official_source_keys,
)
from app.collectors.registry import COLLECTOR_REGISTRY
from app.collectors.security import credential_status
from app.core.config import settings
from app.db.models import (
    ArtistMasterModel,
    CollectorRunItemModel,
    CollectorRunModel,
    NormalizedMetricModel,
    RawSnapshotModel,
    RawSourceModel,
)
from app.schemas.external_ingestion_v3 import (
    V34CredentialSourceStatus,
    V34CredentialStatusResponse,
    V34OfficialProbeRequest,
    V34OfficialProbeResponse,
    V34OfficialProbeResultRecord,
)
from app.services.v3_external_ingestion_architecture_service import V3ExternalIngestionArchitectureService


class V3ExternalAPIProbeService:
    """Coordinate V3.4-B official API diagnostics and probes."""

    def __init__(self, db: Session) -> None:
        self.db = db
        # Keep A registries populated because B builds on those contracts.
        self.architecture = V3ExternalIngestionArchitectureService(db)
        self.architecture.ensure_registries()

    def credential_status(self) -> V34CredentialStatusResponse:
        """Return sanitized configured/missing status for V3.4-B official APIs."""
        records: list[V34CredentialSourceStatus] = []
        for contract in COLLECTOR_REGISTRY:
            if contract.source_key not in set(official_source_keys()):
                continue
            status_by_var = _credential_status_for_contract(contract.credential_env_vars)
            configured = _is_configured(contract.source_key, status_by_var, contract.can_run_without_credentials)
            records.append(
                V34CredentialSourceStatus(
                    source_key=contract.source_key,
                    source_name=contract.source_name,
                    collector_key=contract.collector_key,
                    requires_credentials=contract.requires_credentials,
                    credential_env_vars=list(contract.credential_env_vars),
                    credential_status=status_by_var,
                    configured_status="configured" if configured else "not_configured",
                    can_run_real_probe=configured,
                    official_api_preferred=True,
                    next_action=_next_action(contract.source_key, configured),
                )
            )
        return V34CredentialStatusResponse(
            block="V3.4-B",
            total=len(records),
            configured=sum(1 for item in records if item.configured_status == "configured"),
            not_configured=sum(1 for item in records if item.configured_status != "configured"),
            sources=records,
            secret_values_exposed=False,
        )

    def run_official_probes(self, request: V34OfficialProbeRequest) -> V34OfficialProbeResponse:
        """Run real or planned official API probes according to the request."""
        sources = request.sources or official_source_keys()
        sources = [source for source in sources if source in official_source_keys()]
        targets = self._artist_targets(request.limit)
        started_at = utc_now()
        warnings: list[str] = []
        if not targets:
            warnings.append("artist_master has no is_2026_artist=true rows. Rebuild V3.3 before probes.")
        if request.persist and not request.execute_real_calls:
            warnings.append("persist=true was ignored because execute_real_calls=false.")

        collector_run: CollectorRunModel | None = None
        if request.persist and request.execute_real_calls:
            collector_run = CollectorRunModel(
                run_key=f"v3_4_b_official_probe_{int(started_at.timestamp())}",
                status=CollectorRunStatus.RUNNING.value,
                dry_run=False,
                is_active_for_features=False,
                artist_scope=request.artist_scope,
                artist_count=len(targets),
                processed_count=0,
                source_keys_json=sources,
                manifest_payload={
                    "block": "V3.4-B",
                    "artist_scope": request.artist_scope,
                    "artist_count": len(targets),
                    "sources": sources,
                    "limit": request.limit,
                    "execute_real_calls": request.execute_real_calls,
                    "persist": request.persist,
                    "started_by": request.started_by,
                    "generated_at_utc": started_at.isoformat(),
                },
                warning_payload=[],
                started_by=request.started_by,
                started_at=started_at,
            )
            self.db.add(collector_run)
            self.db.flush()

        results: list[V34OfficialProbeResultRecord] = []
        snapshots_created = 0
        snapshots_reused = 0
        metrics_created = 0
        run_items_created = 0
        for target in targets:
            for source_key in sources:
                started_item = time.perf_counter()
                collector = official_collector_for_source(source_key)
                result = self._planned_result(collector.source_key, target)
                if request.execute_real_calls:
                    result = collector.probe_artist(target)
                duration_ms = int((time.perf_counter() - started_item) * 1000)
                raw_snapshot_id: int | None = None
                metric_count = 0
                feature_candidate_count = 0

                if collector_run is not None:
                    raw_snapshot_id, reused = self._persist_snapshot_if_available(result, collector_run.id)
                    snapshots_created += 1 if raw_snapshot_id is not None and not reused else 0
                    snapshots_reused += 1 if raw_snapshot_id is not None and reused else 0
                    metric_count, feature_candidate_count = self._persist_metrics_if_available(result, collector_run.id, raw_snapshot_id, skip_if_snapshot_reused=reused)
                    metrics_created += metric_count
                    run_item = CollectorRunItemModel(
                        collector_run_id=collector_run.id,
                        canonical_artist_key=target.canonical_artist_key,
                        source_key=result.source_key,
                        collector_key=result.collector_key,
                        status=result.status,
                        raw_snapshot_id=raw_snapshot_id,
                        normalized_metric_count=metric_count,
                        profile_candidate_count=result.profile_candidate_count,
                        feature_candidate_metric_count=feature_candidate_count,
                        duration_ms=duration_ms,
                        http_status=result.http_status,
                        error_type=result.status if result.status not in {CollectorStatus.SUCCEEDED.value, CollectorStatus.PARTIAL.value} else None,
                        safe_error_message=result.safe_error_message,
                        retry_count=0,
                        quota_cost_estimated=result.quota_cost_estimated,
                        item_payload={"block": "V3.4-B", "profile_name": result.profile_name, "source_url": result.source_url},
                    )
                    self.db.add(run_item)
                    run_items_created += 1

                results.append(
                    V34OfficialProbeResultRecord(
                        canonical_artist_key=target.canonical_artist_key,
                        artist_name=target.display_name,
                        source_key=result.source_key,
                        collector_key=result.collector_key,
                        status=result.status,
                        confidence=result.confidence,
                        profile_name=result.profile_name,
                        source_url=result.source_url,
                        external_id=result.external_id,
                        metric_keys=[metric.metric_key for metric in result.metrics],
                        metric_count=len(result.metrics),
                        feature_candidate_metric_count=sum(1 for metric in result.metrics if metric.feature_candidate),
                        profile_candidate_count=result.profile_candidate_count,
                        unavailable_metric_keys=list(result.normalized_hint_payload.get("unavailable_metric_keys", [])),
                        field_presence=dict(result.normalized_hint_payload.get("field_presence", {})),
                        official_api_limitation=result.normalized_hint_payload.get("official_api_limitation"),
                        persisted_raw_snapshot_id=raw_snapshot_id,
                        safe_error_message=result.safe_error_message,
                        quota_cost_estimated=result.quota_cost_estimated,
                    )
                )

        finished_at = utc_now()
        if collector_run is not None:
            collector_run.processed_count = len(targets)
            collector_run.status = CollectorRunStatus.COMPLETED_WITH_WARNINGS.value if warnings else CollectorRunStatus.COMPLETED.value
            collector_run.warning_payload = warnings
            collector_run.finished_at = finished_at
            collector_run.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            self.db.commit()
        else:
            self.db.rollback()

        return V34OfficialProbeResponse(
            block="V3.4-B",
            artist_scope=request.artist_scope,
            artist_count=self._total_2026_artists(),
            selected_artist_count=len(targets),
            selected_sources=sources,
            execute_real_calls=request.execute_real_calls,
            persist=request.persist and request.execute_real_calls,
            collector_run_id=collector_run.id if collector_run is not None else None,
            raw_snapshots_created=snapshots_created,
            raw_snapshots_reused=snapshots_reused,
            normalized_metrics_created=metrics_created,
            collector_run_items_created=run_items_created,
            warnings=warnings,
            results=results,
        )

    def _artist_targets(self, limit: int | None) -> list[ArtistProbeTarget]:
        """Return canonical Nexus 2026 artist targets for probes."""
        statement = (
            select(ArtistMasterModel)
            .where(ArtistMasterModel.is_2026_artist.is_(True))
            .order_by(ArtistMasterModel.is_top_artist.desc(), ArtistMasterModel.display_name.asc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        rows = list(self.db.scalars(statement).all())
        return [
            ArtistProbeTarget(
                canonical_artist_key=row.canonical_artist_key,
                display_name=row.display_name,
                normalized_name=row.normalized_name,
                source_artist_slug=row.source_artist_slug,
            )
            for row in rows
        ]

    def _total_2026_artists(self) -> int:
        """Return total canonical Nexus 2026 artist count."""
        return int(
            self.db.scalar(select(func.count()).select_from(ArtistMasterModel).where(ArtistMasterModel.is_2026_artist.is_(True)))
            or 0
        )

    def _planned_result(self, source_key: str, target: ArtistProbeTarget) -> OfficialProbeResult:
        """Return an offline plan result without making real external calls."""
        collector = official_collector_for_source(source_key)
        configured = collector.configured()
        return OfficialProbeResult(
            source_key=source_key,
            collector_key=collector.contract.collector_key,
            canonical_artist_key=target.canonical_artist_key,
            status=CollectorStatus.SKIPPED.value if configured else CollectorStatus.NOT_CONFIGURED.value,
            confidence=collector.contract.confidence,
            safe_error_message=None if configured else "Required credentials/access are missing.",
        )

    def _persist_snapshot_if_available(self, result: OfficialProbeResult, collector_run_id: int) -> tuple[int | None, bool]:
        """Persist raw payload idempotently and return snapshot id plus reused flag."""
        if not result.raw_payload:
            return None, False
        captured_at = utc_now()
        snapshot_key = build_snapshot_key(
            source_key=result.source_key,
            canonical_artist_key=result.canonical_artist_key,
            collector_key=result.collector_key,
            payload=result.raw_payload,
            captured_at=captured_at,
        )
        existing = self.db.scalar(select(RawSnapshotModel).where(RawSnapshotModel.snapshot_key == snapshot_key))
        if existing is not None:
            return existing.id, True
        raw_source = self.db.scalar(select(RawSourceModel).where(RawSourceModel.source_key == result.source_key))
        snapshot = RawSnapshotModel(
            raw_source_id=raw_source.id if raw_source else None,
            source_key=result.source_key,
            entity_type="artist",
            entity_key=result.canonical_artist_key,
            canonical_artist_key=result.canonical_artist_key,
            collector_run_id=collector_run_id,
            collector_key=result.collector_key,
            snapshot_key=snapshot_key,
            captured_at=captured_at,
            source_reported_at=None,
            source_url=result.source_url,
            extraction_method="official_api_probe",
            confidence=result.confidence,
            status=result.status,
            schema_version="v3.4-b",
            collector_version=str(result.normalized_hint_payload.get("schema_revision", "v3.4-b")),
            normalizer_version=str(result.normalized_hint_payload.get("schema_revision", "v3.4-b")),
            content_hash=content_hash(result.raw_payload),
            raw_payload=result.raw_payload,
            normalized_hint_payload=result.normalized_hint_payload,
            notes="V3.4-B official API probe raw snapshot. Not a prediction or ML output.",
        )
        self.db.add(snapshot)
        self.db.flush()
        return snapshot.id, False

    def _persist_metrics_if_available(
        self,
        result: OfficialProbeResult,
        collector_run_id: int,
        raw_snapshot_id: int | None,
        *,
        skip_if_snapshot_reused: bool = False,
    ) -> tuple[int, int]:
        """Persist normalized metric candidates for a raw snapshot.

        V3.4-A originally skipped metric insertion whenever a raw snapshot was
        reused, which avoided inflated counts but created a subtle bug during
        collector upgrades: if the same raw payload was captured with a richer
        normalizer later, the endpoint reused the old snapshot and never wrote
        the newly available metrics.

        V3.4-B needs Spotify to persist the full official artist metrics when
        they exist. Therefore a reused snapshot is still allowed, but we insert
        only missing metric keys for that snapshot. This keeps idempotency while
        allowing normalizer upgrades to backfill newly supported metrics.
        """
        if raw_snapshot_id is None or not result.metrics:
            return 0, 0

        existing_metric_keys: set[str] = set(

                self.db.scalars(
                    select(NormalizedMetricModel.metric_key).where(
                        NormalizedMetricModel.raw_snapshot_id == raw_snapshot_id,
                        NormalizedMetricModel.source_key == result.source_key,
                        NormalizedMetricModel.canonical_artist_key == result.canonical_artist_key,
                    )
                ).all()
        )

        created = 0
        feature_candidates = 0
        captured_at = utc_now()
        for metric in result.metrics:
            if metric.metric_key in existing_metric_keys:
                continue
            row = NormalizedMetricModel(
                raw_snapshot_id=raw_snapshot_id,
                source_key=result.source_key,
                entity_type="artist",
                entity_key=result.canonical_artist_key,
                canonical_artist_key=result.canonical_artist_key,
                collector_run_id=collector_run_id,
                collector_key=result.collector_key,
                metric_key=metric.metric_key,
                metric_value_numeric=metric.metric_value_numeric,
                metric_value_text=metric.metric_value_text,
                metric_unit=metric.metric_unit,
                value_type=metric.value_type,
                normalized_at=captured_at,
                captured_at=captured_at,
                source_reported_at=None,
                confidence=metric.confidence,
                source_url=result.source_url,
                extraction_method="official_api_probe",
                source_method="normalized_from_v3_4_b_probe",
                collector_version=str(result.normalized_hint_payload.get("schema_revision", "v3.4-b")),
                normalizer_version=str(result.normalized_hint_payload.get("schema_revision", "v3.4-b")),
                metric_schema_version="v3.4",
                feature_candidate=metric.feature_candidate,
                is_diagnostic_only=metric.is_diagnostic_only,
                notes=metric.notes or "V3.4-B metric candidate. Final gates happen in V3.4-D/V3.8.",
                raw_payload={"source_key": result.source_key, "block": "V3.4-B"},
            )
            self.db.add(row)
            created += 1
            feature_candidates += 1 if metric.feature_candidate else 0
        return created, feature_candidates


def _credential_status_for_contract(required_vars: Iterable[str]) -> dict[str, str]:
    """Return status for env variables without exposing values."""
    values = {name: _credential_value(name) for name in required_vars}
    return credential_status(values, tuple(required_vars))


def _credential_value(name: str) -> str | None:
    """Read credential value from Settings; never return it outside status helpers."""
    value = getattr(settings, name, None)
    if value in (None, ""):
        return None
    return str(value)


def _is_configured(source_key: str, status_by_var: dict[str, str], can_run_without_credentials: bool) -> bool:
    """Return source-level configured status."""
    if source_key == "musicbrainz_api":
        return bool(settings.MUSICBRAINZ_USER_AGENT)
    if not status_by_var:
        return True
    return all(status == "configured" for status in status_by_var.values()) or can_run_without_credentials


def _next_action(source_key: str, configured: bool) -> str:
    """Return the next setup action for a source."""
    if configured:
        return "Ready for a controlled V3.4-B probe."
    if source_key == "youtube_data_api":
        return "Create a Google Cloud API key with YouTube Data API v3 enabled and set YOUTUBE_API_KEY in backend/.env."
    if source_key == "soundcloud_public_api":
        return "Attempt official SoundCloud app/API access; if unavailable, continue with V3.4-C metadata-only fallback."
    if source_key == "spotify_web_api":
        return "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in backend/.env."
    if source_key == "lastfm_api":
        return "Set LASTFM_API_KEY in backend/.env."
    if source_key == "musicbrainz_api":
        return "Set a descriptive MUSICBRAINZ_USER_AGENT in backend/.env."
    return "Configure credentials or document the source as unavailable."