type UserNarrativeMixPageProps = {
  personSlug: string;
};

export function UserNarrativeMixPage({ personSlug }: UserNarrativeMixPageProps) {
  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="content-stack">
          <article className="panel">
            <h2>Narrative Mix</h2>
            <p className="status-copy">
              Skeleton page for user-level narrative mix exploration.
            </p>
            <p className="status-copy">Current user: {personSlug}</p>
            <p className="status-copy">
              Planned focus: topic-share over time and narrative composition shifts.
            </p>
          </article>
        </div>
      </article>
    </section>
  );
}
