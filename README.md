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

## Run the scaffold

These commands verify the current foundation only. They do not require the real Twitter API integration yet.

### One command for local dev

From the repo root:

```bash
./scripts/dev.sh
```

That script will:
- create `.venv/` if needed
- install backend dependencies if needed
- create `backend/.env` from `.env.example` if missing
- install frontend dependencies if needed
- start the FastAPI backend on `127.0.0.1:8000`
- start the Vite frontend on `127.0.0.1:5173`

When both are running, open [http://127.0.0.1:5173](http://127.0.0.1:5173).

The homepage will run the backend health check automatically. You should see:
- a visible `Health check succeeded.` message on the page
- the returned JSON rendered on the page
- a matching success log in the browser console
- a database status inside the returned health payload

## Postgres and migrations

The portable local setup for this repo is a Docker-managed Postgres instance defined in [compose.yaml](/Users/michaelsullivan/Code/ChartProject/compose.yaml). That gives you the same database shape and credentials on any machine with Docker installed.

### Recommended setup

1. Install and start Docker Desktop.
2. From the repo root, run:

```bash
./scripts/setup-db.sh
```

That script will:
- create `.venv/` if needed
- install backend dependencies if needed
- create `backend/.env` from [backend/.env.example](/Users/michaelsullivan/Code/ChartProject/backend/.env.example) if missing
- start the `postgres:16` container from [compose.yaml](/Users/michaelsullivan/Code/ChartProject/compose.yaml)
- wait for Postgres to become ready
- run `alembic upgrade head`

The default local database URL is:

```env
CHART_DATABASE_URL=postgresql+psycopg://chartproject:chartproject@localhost:5433/chartproject
```

This applies [0001_initial_core_schema.py](/Users/michaelsullivan/Code/ChartProject/backend/migrations/versions/0001_initial_core_schema.py).

### Verify database connectivity

After `./scripts/setup-db.sh`, start the app:

```bash
./scripts/dev.sh
```

Then open [http://127.0.0.1:5173](http://127.0.0.1:5173).

When Postgres is reachable, the health payload should include:

```json
"database": {
  "connected": true,
  "status": "ok",
  "detail": "Connection succeeded."
}
```

### Move to another machine

To recreate the same local environment elsewhere:

1. Clone the repo.
2. Install Docker Desktop.
3. Run `./scripts/setup-db.sh`.
4. Run `./scripts/dev.sh`.

That is the intended portable workflow for local development.

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

### Backend health check

In a separate terminal:

```bash
curl http://127.0.0.1:8000/api/health
```

Expected response:

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

### Frontend

In a separate terminal:

```bash
cd /Users/michaelsullivan/Code/ChartProject/frontend
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173).

If the backend is running, the frontend will load the health status through the Vite `/api` proxy.

## Local structure

```text
backend/
frontend/
data/
docs/
ProjectPlan.md
```
