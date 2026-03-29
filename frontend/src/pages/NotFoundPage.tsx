export function NotFoundPage() {
  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="not-found-state">
          <p className="eyebrow dashboard-eyebrow">Overview Error</p>
          <h1 className="not-found-title">Overview not found</h1>
          <p className="dashboard-subtitle">
            The requested overview route does not match any locally configured page.
          </p>
        </div>
      </article>
    </section>
  );
}
