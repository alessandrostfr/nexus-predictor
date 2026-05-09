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
- V3.4-A closed: collector architecture, contracts, security, idempotency and registries.
- Current operative macropaso: V3.4-B — credentials and official API probes.

## V3.4 subroadmap rule

V3.4 is temporarily split into six internal macropasos:

1. V3.4-A — Architecture, contracts, security, idempotency and registries. ✅ closed
2. V3.4-B — Credentials and official API probes. ← current
3. V3.4-C — yt-dlp, controlled scraping and open-source evaluation.
4. V3.4-D — Normalization, quality, readiness and manual fallback.
5. V3.4-E — Real ingestion run for all Nexus 2026 artists.
6. V3.4-F — Prefect, admin review and final block checks.

After V3.4-F, continue the main roadmap at V3.5.

## V3.4-B official API probes

V3.4-B introduces controlled official API probes for:

- Spotify Web API;
- Last.fm API;
- MusicBrainz Web Service;
- YouTube Data API;
- SoundCloud official/access probe.

Tests remain offline. Real calls require explicit opt-in with `execute_real_calls=true`; persistence requires both `execute_real_calls=true` and `persist=true`.

## ML honesty reminder

V3.4 data is evidence and potential future input. It is not prediction, not a label, and not ML output.
