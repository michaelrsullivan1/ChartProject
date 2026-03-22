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

The backend health endpoint now attempts a real database connection. Until Postgres is running and migrated, the API health status will likely be `degraded`.

### 1. Create the local database

If PostgreSQL is already installed locally and `createdb` is available:

```bash
createdb chartproject
```

If your local Postgres user is not `postgres`, update `CHART_DATABASE_URL` in [backend/.env.example](/Users/michaelsullivan/Code/ChartProject/backend/.env.example) and then copy it into `backend/.env`.

### 2. Apply the first migration

```bash
cd /Users/michaelsullivan/Code/ChartProject
source .venv/bin/activate
cd backend
alembic upgrade head
```

This applies [0001_initial_core_schema.py](/Users/michaelsullivan/Code/ChartProject/backend/migrations/versions/0001_initial_core_schema.py).

### 3. Verify database connectivity

Run the local dev stack:

```bash
cd /Users/michaelsullivan/Code/ChartProject
./scripts/dev.sh
```

Then open [http://127.0.0.1:5173](http://127.0.0.1:5173).

When Postgres is reachable, the JSON on the page should include:

```json
"database": {
  "connected": true,
  "status": "ok",
  "detail": "Connection succeeded."
}
```

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
