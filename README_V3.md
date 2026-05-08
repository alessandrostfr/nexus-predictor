# Nexus Predictor V3 — ML-first operational guide

Nexus Predictor V3 rebuilds the predictive core around real Machine Learning.
This guide is intentionally strict: heuristics, manual scoring and optimization
must never be presented as final ML.

## Central rule

Nothing is called ML unless it has:

- training data;
- features;
- target or documented proxy;
- a real training step such as `fit()`;
- validation metrics;
- persisted predictions;
- model/version metadata.

## Current roadmap position

- V3.0 closed: predictive audit and ML-first branch guardrails.
- V3.1 closed: continuous Nexus 2026 event contract.
- V3.2 closed: ML-ready data foundation.
- V3.3 closed: artist identity resolution.
- V3.4 active: external ingestion factory, executed through the approved V3.4 subroadmap.
- Current operative macropaso: V3.4-A — collector architecture, contracts, security, idempotency and registries.

## V3.4 subroadmap rule

V3.4 is temporarily split into six internal macropasos:

1. V3.4-A — Architecture, contracts, security, idempotency and registries.
2. V3.4-B — Credentials and official API probes.
3. V3.4-C — yt-dlp, controlled scraping and open-source evaluation.
4. V3.4-D — Normalization, quality, readiness and manual fallback.
5. V3.4-E — Real ingestion run for all Nexus 2026 artists.
6. V3.4-F — Prefect, admin review and final block checks.

After V3.4-F, continue the main roadmap at V3.5.

## V3.4-A architecture foundation

V3.4-A creates the offline collector architecture only. It does not call external APIs.

New concepts:

- `source_tool_evaluations`: evaluated APIs/tools/scrapers/fallbacks.
- `collector_runs`: run manifests and rollback/is_active_for_features controls.
- `collector_run_items`: per-artist/per-source statuses.
- `backend/app/collectors/*`: shared collector contracts, cache/rate-limit policy, secret safety and deduplication helpers.
- `raw_snapshots` and `normalized_metrics` gain canonical artist, run, timestamp and version lineage fields.

## ML honesty reminder

V3.4 data is evidence and potential future input. It is not prediction, not a label, and not ML output.
