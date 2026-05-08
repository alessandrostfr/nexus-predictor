# V3.0 closure decisions — Nexus Predictor V3

This file closes the alignment questions required by roadmap block V3.0.

V3.0 must not be committed until this file contains a real start commit hash.

## Decision 1 — Exact commit where V3 starts

Replace the placeholder below with the output of:

```powershell
git rev-parse HEAD
```

Use the commit that existed before committing V3.0 documentation/audit changes.

```text
V3_START_COMMIT=141c70366ccf63e87cdec541b44dbbf119eff745
```

Why this matters:

- V3 must be reproducible.
- We need to know exactly which V2/V2.11 state was used as the base.
- Future audits can compare V2 predictive behavior against V3 changes.

## Decision 2 — Branch

```text
V3_BRANCH=refactor/v3-ml-first
```

The V3.0 validation script expects this branch.

## Decision 3 — Public product name and technical subtitle

```text
PUBLIC_PRODUCT_NAME=Nexus Predictor
TECHNICAL_SUBTITLE=V3 — ML-first
```

Decision:

- Keep the visible product name as **Nexus Predictor**.
- Use **V3 — ML-first** as technical/internal subtitle in docs, admin/debug context and project explanations.
- Do not rename the product UI unless Alessandro explicitly asks later.

Reason:

- The product identity already works.
- The important change is the predictive core, not the public brand.
- "ML-first" is useful as a technical qualifier, but it should not make the user-facing product name clunky.

## Decision 4 — Current V2 predictive layer status

```text
CURRENT_V2_PREDICTIVE_LAYER_STATUS=not_final_ml
```

The current V2 predictive layer is useful but must be classified honestly:

- Demand: scoring/baseline candidate.
- Probable timetable: heuristic/baseline candidate.
- Room risk: heuristic/scoring.
- Optimized timetable: optimization, not ML.
- Evidence/Spotify/historical data: reusable input data.

## Decision 5 — V3.0 code-change policy

```text
V3_0_RUNTIME_POLICY=docs_and_audit_only
```

V3.0 should not modify:

- visible frontend runtime;
- prediction runtime behavior;
- database schema;
- API behavior.

Allowed changes:

- `README_V3.md`;
- `docs/ROADMAP_POSITION.md`;
- `docs/v3-predictive-audit.md`;
- `docs/v3-0-closure-decisions.md`;
- `backend/scripts/check_v3_predictive_audit.py`.

## Decision 6 — Next block

```text
NEXT_BLOCK=V3.1 — Contrato real Nexus 2026 y calendario continuo
```

V3.1 starts only after V3.0 is committed.

## Final V3.0 closure checklist

- [ ] `V3_START_COMMIT` has been replaced with a real Git hash.
- [ ] `git branch --show-current` returns `refactor/v3-ml-first`.
- [ ] `python backend/scripts/check_v3_predictive_audit.py` passes.
- [ ] `pytest` passes from `backend/`.
- [ ] Commit created with message: `audit predictive core for ml first v3`.

## Progress after commit

```text
V3_PROGRESS_AFTER_COMMIT=5%
```
