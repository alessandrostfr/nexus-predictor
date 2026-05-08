# V3.4 external ingestion contract

This document defines the architecture contract introduced in **V3.4-A — Arquitectura, contratos, seguridad, idempotencia y registros**.

V3.4-A does not collect live data. It creates the structure required so later macropasos can collect external data without breaking ML honesty.

## Central rule

No external value can become a future ML feature unless it has:

- canonical artist identity;
- source key;
- collector key and version;
- normalizer version;
- raw snapshot or documented manual evidence;
- confidence;
- extraction method;
- cache policy;
- rate-limit policy;
- feature-candidate gate.

## Source registry

The source registry is backed by `raw_sources` and by the static contracts in `backend/app/collectors/registry.py`.

Each source contract defines:

- `source_key`;
- `source_type`;
- `access_method`;
- `requires_credentials`;
- `credential_env_vars`;
- `rate_limit_policy`;
- `cache_policy`;
- `legal_risk`;
- `ml_value`;
- `cost_level`;
- `supported_entities`;
- `can_run_without_credentials`;
- `collector_version`;
- `normalizer_version`;
- `schema_version`.

Credential values are never returned, logged or persisted.

## Tool registry

The table `source_tool_evaluations` stores evaluated APIs, libraries, scrapers and fallbacks. It exists so we do not create scrapers blindly.

Minimum evaluated tools in V3.4-A:

- Spotify Web API direct client;
- Last.fm API direct client;
- MusicBrainz Web Service;
- YouTube Data API;
- SoundCloud official/access probe;
- yt-dlp metadata-only candidate;
- NewPipeExtractor spike;
- httpx + BeautifulSoup static pages;
- Playwright last resort.

## Runs

`collector_runs` stores execution manifests.

Important fields:

- `status`: `running`, `completed`, `completed_with_warnings`, `failed`, `cancelled`;
- `dry_run`;
- `is_active_for_features`;
- `artist_scope`;
- `artist_count`;
- `processed_count`;
- `manifest_payload`;
- `warning_payload`.

A failed or cancelled run must not feed future feature engineering.

## Run items

`collector_run_items` stores per-artist/per-source status.

Important fields:

- `collector_run_id`;
- `canonical_artist_key`;
- `source_key`;
- `collector_key`;
- `status`;
- `raw_snapshot_id`;
- `normalized_metric_count`;
- `profile_candidate_count`;
- `feature_candidate_metric_count`;
- `safe_error_message`.

## Raw snapshots and metrics

V3.4-A extends the V3.2 tables with:

- `canonical_artist_key`;
- `collector_run_id`;
- `collector_key`;
- `source_reported_at`;
- `collector_version`;
- `normalizer_version`.

`normalized_metrics` also gets:

- `metric_schema_version`;
- `is_diagnostic_only`.

These fields exist before live ingestion so later data can be replayed, audited and filtered safely.
