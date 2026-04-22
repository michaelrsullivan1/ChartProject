import { useEffect, useState } from "react";

import { fetchPodcastPerson, type PodcastPersonResponse } from "../api/podcastPerson";
import { DashboardLoadingState } from "../components/DashboardLoadingState";

const integerFormatter = new Intl.NumberFormat("en-US");

const fullDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const monthFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

type PodcastPersonPageProps = {
  personSlug: string;
};

export function PodcastPersonPage({ personSlug }: PodcastPersonPageProps) {
  const [payload, setPayload] = useState<PodcastPersonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    async function loadView() {
      try {
        const response = await fetchPodcastPerson(personSlug, controller.signal);
        setPayload(response);
        setError(null);
      } catch (loadError) {
        if (controller.signal.aborted) {
          return;
        }
        setPayload(null);
        setError(loadError instanceof Error ? loadError.message : "Unknown podcast fetch failure");
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    setIsLoading(true);
    setError(null);
    setPayload(null);
    void loadView();

    return () => {
      controller.abort();
    };
  }, [personSlug]);

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        {isLoading ? <DashboardLoadingState /> : null}
        {!isLoading && error ? <p className="status-copy">{error}</p> : null}
        {!isLoading && payload ? <PodcastPersonContent payload={payload} /> : null}
      </article>
    </section>
  );
}

function PodcastPersonContent({ payload }: { payload: PodcastPersonResponse }) {
  return (
    <div className="podcast-person-page">
      <div className="metric-strip metric-strip-dashboard">
        <article className="metric-card">
          <p className="metric-label">Person</p>
          <p className="metric-value">{payload.subject.name}</p>
          <p className="metric-note">{payload.subject.slug}</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Appearances</p>
          <p className="metric-value">{integerFormatter.format(payload.summary.appearance_count)}</p>
          <p className="metric-note">Across the imported podcast corpus</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Beliefs</p>
          <p className="metric-value">{integerFormatter.format(payload.summary.belief_count)}</p>
          <p className="metric-note">
            Source profile total: {integerFormatter.format(payload.summary.source_total_beliefs ?? 0)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Range Start</p>
          <p className="metric-value">{formatFullDate(payload.summary.range_start)}</p>
          <p className="metric-note">First dated appearance in imported data</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Range End</p>
          <p className="metric-value">{formatFullDate(payload.summary.range_end)}</p>
          <p className="metric-note">Latest dated appearance in imported data</p>
        </article>
      </div>

      <div className="content-grid">
        <article className="panel">
          <h2>Top Shows</h2>
          <div className="bitcoin-table-shell">
            <table className="bitcoin-table">
              <thead>
                <tr>
                  <th>Show</th>
                  <th>Appearances</th>
                </tr>
              </thead>
              <tbody>
                {payload.top_shows.map((row) => (
                  <tr key={row.show_slug}>
                    <td>{row.show_name}</td>
                    <td>{integerFormatter.format(row.appearance_count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel">
          <h2>Top Topics</h2>
          <div className="bitcoin-table-shell">
            <table className="bitcoin-table">
              <thead>
                <tr>
                  <th>Topic</th>
                  <th>Beliefs</th>
                </tr>
              </thead>
              <tbody>
                {payload.top_topics.map((row) => (
                  <tr key={row.topic}>
                    <td>{row.topic}</td>
                    <td>{integerFormatter.format(row.belief_count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </div>

      <article className="panel">
        <h2>Monthly Topic Counts</h2>
        <div className="bitcoin-table-shell">
          <table className="bitcoin-table">
            <thead>
              <tr>
                <th>Month</th>
                <th>Topic</th>
                <th>Beliefs</th>
              </tr>
            </thead>
            <tbody>
              {payload.monthly_topic_counts.map((row) => (
                <tr key={`${row.month_start}-${row.topic}`}>
                  <td>{formatMonth(row.month_start)}</td>
                  <td>{row.topic}</td>
                  <td>{integerFormatter.format(row.belief_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      <article className="panel">
        <h2>Appearances</h2>
        <div className="bitcoin-table-shell">
          <table className="bitcoin-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Show</th>
                <th>Episode</th>
              </tr>
            </thead>
            <tbody>
              {payload.appearances.map((row) => (
                <tr key={`${row.published_at}-${row.show_name}-${row.episode_title}`}>
                  <td>{formatFullDate(row.published_at)}</td>
                  <td>{row.show_name}</td>
                  <td>{row.episode_title}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      <article className="panel">
        <h2>Recent Beliefs</h2>
        <div className="bitcoin-table-shell">
          <table className="bitcoin-table bitcoin-table-detail">
            <thead>
              <tr>
                <th>Date</th>
                <th>Show</th>
                <th>Topic</th>
                <th>Atomic Belief</th>
                <th>Quote</th>
              </tr>
            </thead>
            <tbody>
              {payload.recent_beliefs.map((row, index) => (
                <tr key={`${row.published_at}-${row.atomic_belief}-${index}`}>
                  <td>{formatFullDate(row.published_at)}</td>
                  <td>{row.show_name}</td>
                  <td>{row.topic ?? "Unlabeled"}</td>
                  <td>{row.atomic_belief}</td>
                  <td>{row.quote}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </div>
  );
}

function formatFullDate(value: string | null): string {
  if (!value) {
    return "Unknown";
  }
  return fullDateFormatter.format(new Date(value));
}

function formatMonth(value: string): string {
  return monthFormatter.format(new Date(value));
}
