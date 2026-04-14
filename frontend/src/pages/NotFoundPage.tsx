export function NotFoundPage() {
  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="not-found-state">
          <p className="eyebrow dashboard-eyebrow">Route Error</p>
          <h1 className="not-found-title">Route not found</h1>
          <p className="dashboard-subtitle">
            The requested route does not match any published tracked author or settings page.
          </p>
        </div>
      </article>
    </section>
  );
}
