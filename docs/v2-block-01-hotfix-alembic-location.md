# V2.1 hotfix — Alembic migration location

This hotfix moves the V2.1 evidence-layer migration into the active Alembic
script location used by the repository:

- Active script location: `backend/alembic`
- Active versions folder: `backend/alembic/versions`

The previous V2.1 ZIP placed the migration under `backend/migrations/versions`,
which is not read by the current `backend/alembic.ini` configuration.
