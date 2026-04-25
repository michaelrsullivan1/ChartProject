import { useEffect, useMemo, useState } from "react";

import {
  fetchAggregateMoodCohorts,
  fetchAggregateMoodOutliers,
  type AggregateMoodCohortsResponse,
  type AggregateMoodOutlierEntry,
  type AggregateMoodOutliersResponse,
} from "../api/authorOverview";
import { DashboardLoadingState } from "../components/DashboardLoadingState";

const ALL_COHORT_KEY = "__all_tracked_users__";

const numberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 3,
  minimumFractionDigits: 3,
});

const integerFormatter = new Intl.NumberFormat("en-US");

const compactDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

type MoodOutliersPageProps = {
  apiBasePath: string;
};

type CohortOption = {
  key: string;
  tagSlug: string | null;
  tagName: string;
  userCount: number | null;
};

export function MoodOutliersPage({ apiBasePath }: MoodOutliersPageProps) {
  const [outlierPayload, setOutlierPayload] = useState<AggregateMoodOutliersResponse | null>(null);
  const [cohortPayload, setCohortPayload] = useState<AggregateMoodCohortsResponse | null>(null);
  const [selectedCohortKey, setSelectedCohortKey] = useState<string>(ALL_COHORT_KEY);
  const [selectedMoodLabel, setSelectedMoodLabel] = useState<string>("optimism");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const cohortOptions = useMemo(
    () => [
      {
        key: ALL_COHORT_KEY,
        tagSlug: null,
        tagName: "All tracked users",
        userCount: null,
      },
      ...(cohortPayload?.cohorts ?? []).map((cohort) => ({
        key: cohort.tag_slug,
        tagSlug: cohort.tag_slug,
        tagName: cohort.tag_name,
        userCount: cohort.user_count,
      })),
    ],
    [cohortPayload],
  );

  useEffect(() => {
    if (!cohortOptions.some((option) => option.key === selectedCohortKey)) {
      setSelectedCohortKey(ALL_COHORT_KEY);
    }
  }, [cohortOptions, selectedCohortKey]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const cohortTagSlug =
          selectedCohortKey === ALL_COHORT_KEY ? null : selectedCohortKey;
        const [cohorts, outliers] = await Promise.all([
          fetchAggregateMoodCohorts(apiBasePath),
          fetchAggregateMoodOutliers(apiBasePath, "week", undefined, { cohortTagSlug }),
        ]);

        if (cancelled) {
          return;
        }

        setCohortPayload(cohorts);
        setOutlierPayload(outliers);
        setSelectedMoodLabel((current) => {
          if (outliers.model.mood_labels.includes(current)) {
            return current;
          }
          return outliers.model.mood_labels.includes("optimism")
            ? "optimism"
            : (outliers.model.mood_labels[0] ?? "optimism");
        });
        setError(null);
      } catch (loadError) {
        console.error("ChartProject mood outlier request failed", loadError);
        if (!cancelled) {
          setOutlierPayload(null);
          setError(
            loadError instanceof Error ? loadError.message : "Unknown mood outlier request failure",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    setIsLoading(true);
    setError(null);
    void load();

    return () => {
      cancelled = true;
    };
  }, [apiBasePath, selectedCohortKey]);

  const activeMoodOutliers = selectedMoodLabel
    ? outlierPayload?.outliers[selectedMoodLabel] ?? null
    : null;

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace mood-outliers-page">
        {isLoading ? <DashboardLoadingState /> : null}
        {!isLoading && error ? (
          <div className="dashboard-workspace-header">
            <p className="status-copy">{error}</p>
          </div>
        ) : null}
        {!isLoading && outlierPayload && activeMoodOutliers ? (
          <>
            <header className="mood-outliers-header">
              <div className="mood-outliers-header-copy">
                <h2>Mood Outliers</h2>
                <p className="status-copy">
                  Snapshot {formatDate(outlierPayload.generated_at)} for week of{" "}
                  {formatDate(outlierPayload.summary.current_week_start)}.
                </p>
              </div>
              <div className="mood-outliers-controls">
                <label className="chart-control">
                  <span>Cohort</span>
                  <select
                    value={selectedCohortKey}
                    onChange={(event) => setSelectedCohortKey(event.target.value)}
                  >
                    {cohortOptions.map((option) => (
                      <option key={option.key} value={option.key}>
                        {option.userCount !== null
                          ? `${option.tagName} (${integerFormatter.format(option.userCount)})`
                          : option.tagName}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="chart-control">
                  <span>Mood</span>
                  <select
                    value={selectedMoodLabel}
                    onChange={(event) => setSelectedMoodLabel(event.target.value)}
                  >
                    {outlierPayload.model.mood_labels.map((moodLabel) => (
                      <option key={moodLabel} value={moodLabel}>
                        {toTitleCase(moodLabel)}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </header>

            <div className="metric-strip">
              <article className="metric-card">
                <p className="metric-label">Cohort users</p>
                <p className="metric-value">{integerFormatter.format(outlierPayload.cohort.user_count)}</p>
                <p className="metric-note">Users with scored mood history</p>
              </article>
              <article className="metric-card">
                <p className="metric-label">Scored tweets</p>
                <p className="metric-value">
                  {integerFormatter.format(outlierPayload.summary.scored_tweet_count)}
                </p>
                <p className="metric-note">All-time tweets included in snapshot</p>
              </article>
              <article className="metric-card">
                <p className="metric-label">Smoothing</p>
                <p className="metric-value">{outlierPayload.model.smoothing_window_weeks}W WMA</p>
                <p className="metric-note">Weighted by scored tweets per week</p>
              </article>
              <article className="metric-card">
                <p className="metric-label">Baseline</p>
                <p className="metric-value">{outlierPayload.model.baseline_window_weeks}W</p>
                <p className="metric-note">
                  Min {outlierPayload.model.minimum_baseline_weeks} baseline points for self z-score
                </p>
              </article>
            </div>

            <div className="mood-outlier-grid">
              <OutlierTable
                title="Most Elevated"
                rows={activeMoodOutliers.most_elevated}
                scoreKey="self_z_score"
              />
              <OutlierTable
                title="Most Depressed"
                rows={activeMoodOutliers.most_depressed}
                scoreKey="self_z_score"
              />
              <OutlierTable
                title="Fastest Rising"
                rows={activeMoodOutliers.fastest_rising}
                scoreKey="delta_1w"
              />
              <OutlierTable
                title="Fastest Falling"
                rows={activeMoodOutliers.fastest_falling}
                scoreKey="delta_1w"
              />
            </div>
          </>
        ) : null}
      </article>
    </section>
  );
}

type OutlierTableProps = {
  title: string;
  rows: AggregateMoodOutlierEntry[];
  scoreKey: "self_z_score" | "delta_1w";
};

function OutlierTable({ title, rows, scoreKey }: OutlierTableProps) {
  return (
    <article className="panel mood-outlier-panel">
      <h3>{title}</h3>
      <div className="mood-outlier-table-wrap">
        <table className="mood-outlier-table">
          <thead>
            <tr>
              <th>#</th>
              <th>User</th>
              <th>Score</th>
              <th>Current</th>
              <th>1W</th>
              <th>Cohort Z</th>
              <th>Count</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="mood-outlier-empty">
                  No users matched this ranking.
                </td>
              </tr>
            ) : (
              rows.map((row, index) => (
                <tr key={`${title}-${row.platform_user_id}-${index}`}>
                  <td>{index + 1}</td>
                  <td>{row.display_name || row.username}</td>
                  <td>{formatSignedValue(row[scoreKey])}</td>
                  <td>{formatValue(row.current_score)}</td>
                  <td>{formatSignedValue(row.delta_1w)}</td>
                  <td>{formatSignedValue(row.cohort_z_score)}</td>
                  <td>{integerFormatter.format(row.scored_tweet_count)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function formatDate(value?: string | null): string {
  if (!value) {
    return "Unknown";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return compactDateFormatter.format(parsed);
}

function formatValue(value: number | null): string {
  if (value === null) {
    return "N/A";
  }
  return numberFormatter.format(value);
}

function formatSignedValue(value: number | null): string {
  if (value === null) {
    return "N/A";
  }
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${numberFormatter.format(value)}`;
}

function toTitleCase(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}
