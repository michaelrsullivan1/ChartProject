# ChartProject

ChartProject is a local-first X/Twitter research archive and visualization system.

The current foundation follows the architecture in [ProjectPlan.md](/Users/michaelsullivan/Code/ChartProject/ProjectPlan.md):

- `backend/` contains the FastAPI app, SQLAlchemy models, Alembic scaffold, and ingestion entry points
- `frontend/` contains the React + Vite shell
- `data/` holds raw artifacts, exports, and backups outside the app code
- `docs/decisions/` stores lightweight architecture decisions

## Current foundation choices

- Raw API payloads are archived in Postgres first via `raw_ingestion_artifacts`
- Ingestion is generic and designed to accept a target X user ID at runtime
- Frontend work is intentionally minimal until the ingestion and data layers are in place

## Next implementation steps

1. Configure Postgres and environment variables.
2. Run the first Alembic migration for the core tables.
3. Wire the `twitterapi.io` client to the real endpoint details.
4. Run the first generic ingest with a single X user ID.

## Local structure

```text
backend/
frontend/
data/
docs/
ProjectPlan.md
```
