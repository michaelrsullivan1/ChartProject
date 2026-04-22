type UserNarrativeIntensityPageProps = {
  personSlug: string;
};

export function UserNarrativeIntensityPage({ personSlug }: UserNarrativeIntensityPageProps) {
  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="content-stack">
          <article className="panel">
            <h2>Narrative Intensity</h2>
            <p className="status-copy">
              Skeleton page for user-level narrative intensity exploration.
            </p>
            <p className="status-copy">Current user: {personSlug}</p>
            <p className="status-copy">
              Planned focus: beliefs per month, appearances per month, and beliefs per appearance.
            </p>
          </article>
        </div>
      </article>
    </section>
  );
}
