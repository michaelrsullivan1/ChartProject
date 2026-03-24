# ChartProject

ChartProject is a local-first X/Twitter research archive and visualization system.

The architecture source of truth is [ProjectPlan.md](/Users/michaelsullivan/Code/ChartProject/ProjectPlan.md).

## Current state

The local foundation is working end-to-end:

- containerized Postgres
- Alembic migrations
- FastAPI backend health check
- React frontend that confirms backend and database connectivity on page load

If the stack is healthy, the frontend should show:

- `Health check succeeded.`
- backend `status: ok`
- database `status: ok`
- the full JSON health payload rendered on the page

## Quick start

From the repo root:

```bash
./scripts/setup-db.sh
./scripts/dev.sh
```

Then open [http://127.0.0.1:5173](http://127.0.0.1:5173).

## Daily commands

Set up or re-apply the local database:

```bash
./scripts/setup-db.sh
```

Start backend and frontend for local development:

```bash
./scripts/dev.sh
```

Check backend health directly:

```bash
curl http://127.0.0.1:8000/api/health
```

Check the Postgres container:

```bash
docker compose ps
```

Stop the local Postgres container:

```bash
docker compose down
```

## Postgres setup

The local database is intentionally containerized and defined in [compose.yaml](/Users/michaelsullivan/Code/ChartProject/compose.yaml). This is the portable development setup for the repo because it makes the database runtime reproducible across machines.

### Why this setup exists

- same Postgres version on different machines
- less machine-specific configuration drift
- easier to recreate the environment from the repo itself
- easier to move the project to another machine later

### Current local connection details

The backend expects:

```env
CHART_DATABASE_URL=postgresql+psycopg://chartproject:chartproject@localhost:5433/chartproject
```

The host port is `5433`, not `5432`.

This project uses `5433` deliberately so it does not collide with other local Postgres instances that may already be using the default `5432`.

### What `./scripts/setup-db.sh` does

- creates `.venv/` if needed
- installs backend dependencies if needed
- creates `backend/.env` from [backend/.env.example](/Users/michaelsullivan/Code/ChartProject/backend/.env.example) if missing
- starts the `postgres:16` container from [compose.yaml](/Users/michaelsullivan/Code/ChartProject/compose.yaml)
- waits for Postgres to become ready
- runs `alembic upgrade head`

This applies [0001_initial_core_schema.py](/Users/michaelsullivan/Code/ChartProject/backend/migrations/versions/0001_initial_core_schema.py).

## Verification

After `./scripts/setup-db.sh` and `./scripts/dev.sh`, the expected backend health response is:

```json
{
  "status": "ok",
  "app_name": "ChartProject API",
  "environment": "development",
  "database": {
    "connected": true,
    "status": "ok",
    "detail": "Connection succeeded."
  }
}
```

If the frontend is working, that same state should appear visibly in the UI.

## Move to another machine

To recreate the same local environment elsewhere:

1. Clone the repo.
2. Install a Docker-compatible runtime.
3. Run `./scripts/setup-db.sh`.
4. Run `./scripts/dev.sh`.

That is the intended portable workflow for local development.

## Manual backend/frontend commands

If you need to run pieces separately instead of using the scripts:

### Backend

```bash
cd /Users/michaelsullivan/Code/ChartProject
python3 -m venv .venv
source .venv/bin/activate
pip install -e backend

cd backend
cp .env.example .env
uvicorn app.main:app --reload
```

### Frontend

```bash
cd /Users/michaelsullivan/Code/ChartProject/frontend
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173).

## Project layout

```text
backend/
frontend/
data/
docs/
scripts/
ProjectPlan.md
compose.yaml
```

## Current foundation choices

- Raw API payloads are archived in Postgres first via `raw_ingestion_artifacts`
- Ingestion is generic and designed to accept a target X user ID at runtime
- Frontend work is intentionally minimal until the ingestion and data layers are in place

## Next implementation steps

1. Wire the `twitterapi.io` client to the real endpoint details.
2. Run the first generic ingest with a single X user ID.
3. Add backup and restore scripts for moving the database between machines.
4. Start persisting and validating real source data.
