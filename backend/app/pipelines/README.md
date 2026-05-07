# V2 pipelines

This package is intentionally light in V2.0. Real ingestion flows start in V2.3, but the folder is created now to keep the architecture stable:

- `flows/`: Prefect orchestration entrypoints.
- `tasks/`: reusable extraction, normalization and persistence tasks.

Every future pipeline must preserve evidence metadata: source name, URL, captured date, confidence, extraction method and notes.
