type UserBeliefsPageProps = {
  personSlug: string;
};

export function UserBeliefsPage({ personSlug }: UserBeliefsPageProps) {
  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="content-stack">
          <article className="panel">
            <h2>User Beliefs</h2>
            <p className="status-copy">
              Skeleton page for representative beliefs and quote-level exploration.
            </p>
            <p className="status-copy">Current user: {personSlug}</p>
            <p className="status-copy">
              Planned focus: belief exemplars by period and topic, with episode context.
            </p>
          </article>
        </div>
      </article>
    </section>
  );
}
