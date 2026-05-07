# V2.3 pipelines

This package now contains the first real Prefect flow for Nexus Predictor V2.

## Flow

- `flows/external_ingestion_flow.py`: orchestrates V2.3 external ingestion.
- `tasks/external_ingestion_tasks.py`: loads the local research seed, persists data, returns coverage and optionally probes source URLs.

## Run

From `backend/`:

```powershell
python -m app.pipelines.flows.external_ingestion_flow --reset
```

or:

```powershell
python scripts/run_external_ingestion.py --reset
```

## Design rules

Every collected or candidate data point must preserve:

- source name
- source URL when available
- capture date
- confidence
- extraction method
- notes

Network failures are non-blocking. A source can fail and the pipeline still stores the deterministic local research seed.
