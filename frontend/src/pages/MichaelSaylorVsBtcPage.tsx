import { useEffect, useState } from "react";

import {
  fetchMichaelSaylorVsBtc,
  type MichaelSaylorVsBtcResponse,
} from "../api/michaelSaylorVsBtc";

export function MichaelSaylorVsBtcPage() {
  const [payload, setPayload] = useState<MichaelSaylorVsBtcResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadView() {
      try {
        const response = await fetchMichaelSaylorVsBtc("week");
        console.info("ChartProject michael-saylor-vs-btc payload", response);
        if (!cancelled) {
          setPayload(response);
          setError(null);
        }
      } catch (loadError) {
        console.error("ChartProject michael-saylor-vs-btc request failed", loadError);
        if (!cancelled) {
          setPayload(null);
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unknown michael-saylor-vs-btc fetch failure",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadView();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="content-grid">
      <article className="panel panel-accent">
        <h2>Michael Saylor vs BTC endpoint</h2>
        <p className="status-copy">
          Fetches <code>/api/views/michael-saylor-vs-btc?granularity=week</code> and logs the
          response payload to the browser console.
        </p>
        {isLoading ? <p className="status-copy">Loading dedicated view payload...</p> : null}
        {error ? <p className="status-copy">{error}</p> : null}
        {payload ? (
          <>
            <p className="success-banner">Payload loaded and logged to console.</p>
            <dl className="status-grid">
              <div>
                <dt>View</dt>
                <dd>{payload.view}</dd>
              </div>
              <div>
                <dt>Subject</dt>
                <dd>{payload.subject.display_name ?? payload.subject.username}</dd>
              </div>
              <div>
                <dt>Tweet Points</dt>
                <dd>{payload.tweet_series.length}</dd>
              </div>
              <div>
                <dt>BTC Points</dt>
                <dd>{payload.btc_series.length}</dd>
              </div>
            </dl>
          </>
        ) : null}
      </article>

      <article className="panel">
        <h2>Current request</h2>
        <pre className="json-panel">
          {JSON.stringify(
            {
              page: "Michael Saylor vs BTC",
              granularity: "week",
              status: isLoading ? "loading" : error ? "error" : payload ? "loaded" : "idle",
              endpoint: "/api/views/michael-saylor-vs-btc?granularity=week",
            },
            null,
            2,
          )}
        </pre>
      </article>
    </section>
  );
}
