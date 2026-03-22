import type { HealthResponse } from "../types/health";

type HomePageProps = {
  health: HealthResponse | null;
  error: string | null;
};

const foundationItems = [
  "FastAPI app shell with a health endpoint",
  "Core SQLAlchemy models for users, tweets, runs, and raw artifacts",
  "Generic ingestion entry point that accepts a single X user ID",
  "React + Vite shell for later analytical pages",
];

export function HomePage({ health, error }: HomePageProps) {
  return (
    <section className="content-grid">
      <article className="panel">
        <h2>Foundation status</h2>
        <ul className="feature-list">
          {foundationItems.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </article>

      <article className="panel panel-accent">
        <h2>Backend connection</h2>
        {health ? (
          <dl className="status-grid">
            <div>
              <dt>Status</dt>
              <dd>{health.status}</dd>
            </div>
            <div>
              <dt>App</dt>
              <dd>{health.app_name}</dd>
            </div>
            <div>
              <dt>Environment</dt>
              <dd>{health.environment}</dd>
            </div>
          </dl>
        ) : (
          <p className="status-copy">
            {error ?? "Start the backend to verify the API bridge from the frontend."}
          </p>
        )}
      </article>
    </section>
  );
}
