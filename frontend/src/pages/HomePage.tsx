import type { HealthResponse } from "../types/health";

type HomePageProps = {
  health: HealthResponse | null;
  error: string | null;
  isLoading: boolean;
};

const foundationItems = [
  "FastAPI app shell with a health endpoint",
  "Core SQLAlchemy models for users, tweets, runs, and raw artifacts",
  "Working local-first normalization and validation flow for tweet archives",
  "Dedicated Michael Saylor vs BTC endpoint ready for frontend consumption",
];

export function HomePage({ health, error, isLoading }: HomePageProps) {
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
        {isLoading ? (
          <p className="status-copy">Running health check against the local API...</p>
        ) : null}
        {health ? (
          <>
            <p className="success-banner">Health check succeeded.</p>
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
              <div>
                <dt>Database</dt>
                <dd>{health.database.status}</dd>
              </div>
            </dl>
            <pre className="json-panel">{JSON.stringify(health, null, 2)}</pre>
          </>
        ) : (
          <p className="status-copy">
            {error ?? "Start the backend to verify the API bridge from the frontend."}
          </p>
        )}
      </article>
    </section>
  );
}
