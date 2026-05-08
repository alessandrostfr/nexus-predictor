# Roadmap position — Nexus Predictor V3

Current block: **V3.1 — Contrato real Nexus 2026 y calendario continuo**.

## Current status

V3.0 is closed and committed with:

```text
audit predictive core for ml first v3
```

V3.1 starts from the updated V3 branch and fixes the most important time-data
contract before any ML training happens: Nexus 2026 must be represented as one
continuous event, not as separate Friday/Saturday functional days.

## Active branch

```text
refactor/v3-ml-first
```

## Completed before this point

- V1 MVP complete.
- V2.0 Foundations.
- V2.1 Evidence layer.
- V2.2 Spotify real/cache.
- V2.3 External ingestion base.
- V2.4 Social/music platforms and Last.fm foundations.
- V2.5 Multi-genre classification.
- V2.6 Historical timetables 2022-2025.
- V2.7 Demand/popularity scoring model.
- V2.8 Probable 2026 timetable.
- V2.9 Optimized timetable variants.
- V2.10 Premium Next.js + TypeScript frontend.
- V2.11 Professional map and timetable UX.
- V3 roadmap ML-first created.
- V3 roadmap stack section added.
- V3.0 Predictive audit and ML-first branch guardrails.

## V3.1 scope

V3.1 implements:

- `event_contracts` table.
- `event_time_windows` table.
- V3.1 SQLAlchemy models.
- Alembic migration.
- `EventContractService`.
- `/api/v3/events/2026/contract` endpoint.
- `/api/v3/events/2026/time-windows` endpoint.
- `/api/v3/events/2026/contract/validation` endpoint.
- `backend/scripts/check_v3_event_contract.py`.
- Documentation of the continuous 12:00-06:00 rule.
- Adjustment of generated 2026 timetable shells away from Friday/Saturday split.

## V3.1 data contract

```text
Event: Nexus Festival 2026
Start: 13/06/2026 12:00
End: 14/06/2026 06:00
Duration: 18 hours
Functional day key: nexus_day
Visible label: Evento continuo
```

Peak/closing windows may be stored as evidence metadata, but they are not
measured attendance labels and must not be treated as ML targets.

## V3.1 validation

From backend:

```powershell
alembic upgrade head
pytest tests/test_api_v3_event_contract.py
pytest
```

From repo root:

```powershell
python backend/scripts/check_v3_event_contract.py
```

Manual Swagger checks:

```text
POST /api/v3/events/2026/contract/rebuild?reset=true
GET  /api/v3/events/2026/contract
GET  /api/v3/events/2026/time-windows
GET  /api/v3/events/2026/contract/validation
```

Expected facts:

- `duration_hours=18`.
- 18 one-hour windows.
- First boundary `12:00`.
- Last boundary `06:00`.
- `functional_day_key=nexus_day`.
- No 2026 Friday/Saturday split.
- At least one window crosses midnight.

## V3.1 commit

```text
define continuous nexus 2026 event contract
```

## V3.1 progress

```text
5% -> 10%
```

## Next block

After V3.1 is validated and committed, continue with:

```text
V3.2 — Arquitectura de datos ML-ready
```

Do not start model training before V3.1-V3.8 have established data contracts,
identity resolution, ingestion, labels/proxies and features.
