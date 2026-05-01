import { useEffect, useMemo, useState } from "react";

import {
  fetchAggregateCohortMoodOutliers,
  fetchAggregateMoodCohorts,
  fetchAggregateMoodOutliers,
  type AggregateCohortMoodOutlierEntry,
  type AggregateCohortMoodOutliersResponse,
  type AggregateMoodCohortsResponse,
  type AggregateMoodOutlierEntry,
  type AggregateMoodOutliersResponse,
} from "../api/authorOverview";
import { ChartControlSelect } from "../components/ChartControlSelect";
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

type OutlierViewMode = "users" | "cohorts";

export function MoodOutliersPage({ apiBasePath }: MoodOutliersPageProps) {
  const [userOutlierPayload, setUserOutlierPayload] = useState<AggregateMoodOutliersResponse | null>(null);
  const [cohortOutlierPayload, setCohortOutlierPayload] = useState<AggregateCohortMoodOutliersResponse | null>(null);
  const [cohortPayload, setCohortPayload] = useState<AggregateMoodCohortsResponse | null>(null);
  const [selectedCohortKey, setSelectedCohortKey] = useState<string>(ALL_COHORT_KEY);
  const [selectedMoodLabel, setSelectedMoodLabel] = useState<string>("optimism");
  const [viewMode, setViewMode] = useState<OutlierViewMode>("users");
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
        const cohortsPromise = fetchAggregateMoodCohorts(apiBasePath);

        if (viewMode === "users") {
          const cohortTagSlug = selectedCohortKey === ALL_COHORT_KEY ? null : selectedCohortKey;
          const [cohorts, outliers] = await Promise.all([
            cohortsPromise,
            fetchAggregateMoodOutliers(apiBasePath, "week", undefined, { cohortTagSlug }),
          ]);

          if (cancelled) {
            return;
          }

          setCohortPayload(cohorts);
          setUserOutlierPayload(outliers);
          setCohortOutlierPayload(null);
          setSelectedMoodLabel((current) => {
            if (outliers.model.mood_labels.includes(current)) {
              return current;
            }
            return outliers.model.mood_labels.includes("optimism")
              ? "optimism"
              : (outliers.model.mood_labels[0] ?? "optimism");
          });
        } else {
          const [cohorts, cohortOutliers] = await Promise.all([
            cohortsPromise,
            fetchAggregateCohortMoodOutliers(apiBasePath),
          ]);

          if (cancelled) {
            return;
          }

          setCohortPayload(cohorts);
          setCohortOutlierPayload(cohortOutliers);
          setUserOutlierPayload(null);
          setSelectedMoodLabel((current) => {
            if (cohortOutliers.model.mood_labels.includes(current)) {
              return current;
            }
            return cohortOutliers.model.mood_labels.includes("optimism")
              ? "optimism"
              : (cohortOutliers.model.mood_labels[0] ?? "optimism");
          });
        }

        setError(null);
      } catch (loadError) {
        console.error("ChartProject mood outlier request failed", loadError);
        if (!cancelled) {
          setUserOutlierPayload(null);
          setCohortOutlierPayload(null);
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
  }, [apiBasePath, selectedCohortKey, viewMode]);

  const activePayload = viewMode === "users" ? userOutlierPayload : cohortOutlierPayload;
  const activeMoodOutliers = selectedMoodLabel
    ? activePayload?.outliers[selectedMoodLabel] ?? null
    : null;

  const cohortSelectOptions = cohortOptions.map((option) => ({
    value: option.key,
    label:
      option.userCount !== null
        ? `${option.tagName} (${integerFormatter.format(option.userCount)})`
        : option.tagName,
  }));

  const moodSelectOptions = (activePayload?.model.mood_labels ?? []).map((moodLabel) => ({
    value: moodLabel,
    label: toTitleCase(moodLabel),
  }));

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace mood-outliers-page">
        {isLoading ? <DashboardLoadingState /> : null}
        {!isLoading && error ? (
          <div className="dashboard-workspace-header">
            <p className="status-copy">{error}</p>
          </div>
        ) : null}
        {!isLoading && activePayload && activeMoodOutliers ? (
          <>
            <header className="mood-outliers-header">
              <div className="mood-outliers-header-copy">
                <h2>Mood Outliers</h2>
                <p className="status-copy">
                  Snapshot {formatDate(activePayload.generated_at)} for week of{" "}
                  {formatDate(activePayload.summary.current_week_start)}.
                </p>
              </div>
              <div className="mood-outliers-controls">
                <div className="chart-control-card mood-outliers-control-card mood-outliers-view-mode-card">
                  <p className="chart-control-eyebrow">View Mode</p>
                  <div className="chart-toggle-group">
                    <button
                      className={`chart-toggle-button${viewMode === "users" ? " is-active" : ""}`}
                      onClick={() => setViewMode("users")}
                      type="button"
                    >
                      Users
                    </button>
                    <button
                      className={`chart-toggle-button${viewMode === "cohorts" ? " is-active" : ""}`}
                      onClick={() => setViewMode("cohorts")}
                      type="button"
                    >
                      Cohorts
                    </button>
                  </div>
                </div>
                {viewMode === "users" ? (
                  <div className="chart-control-card mood-outliers-control-card">
                    <p className="chart-control-eyebrow">Cohort</p>
                    <label className="chart-control-field">
                      <span className="sr-only">Outlier cohort</span>
                      <ChartControlSelect
                        ariaLabel="Outlier cohort"
                        onChange={setSelectedCohortKey}
                        options={cohortSelectOptions}
                        value={selectedCohortKey}
                      />
                    </label>
                  </div>
                ) : null}
                <div className="chart-control-card mood-outliers-control-card">
                  <p className="chart-control-eyebrow">Mood</p>
                  <label className="chart-control-field">
                    <span className="sr-only">Outlier mood</span>
                    <ChartControlSelect
                      ariaLabel="Outlier mood"
                      onChange={setSelectedMoodLabel}
                      options={moodSelectOptions}
                      value={selectedMoodLabel}
                    />
                  </label>
                </div>
              </div>
            </header>

            <div className="metric-strip">
              <article className="metric-card">
                <p className="metric-label">Eligible users</p>
                <p className="metric-value">{integerFormatter.format(activePayload.summary.cohort_user_count)}</p>
                <p className="metric-note">Users with scored mood history</p>
              </article>
              <article className="metric-card">
                <p className="metric-label">Scored tweets</p>
                <p className="metric-value">
                  {integerFormatter.format(activePayload.summary.scored_tweet_count)}
                </p>
                <p className="metric-note">All-time tweets included in snapshot</p>
              </article>
              <article className="metric-card">
                <p className="metric-label">Smoothing</p>
                <p className="metric-value">{activePayload.model.smoothing_window_weeks}W WMA</p>
                <p className="metric-note">Weighted by scored tweets per week</p>
              </article>
              <article className="metric-card">
                <p className="metric-label">Baseline</p>
                <p className="metric-value">{activePayload.model.baseline_window_weeks}W</p>
                <p className="metric-note">
                  Min {activePayload.model.minimum_baseline_weeks} baseline points for self z-score
                </p>
              </article>
            </div>

            <div className="mood-outlier-grid">
              {viewMode === "users" ? (
                <>
                  <UserOutlierTable
                    title="Most Elevated"
                    rows={activeMoodOutliers.most_elevated as AggregateMoodOutlierEntry[]}
                    scoreKey="self_z_score"
                  />
                  <UserOutlierTable
                    title="Most Depressed"
                    rows={activeMoodOutliers.most_depressed as AggregateMoodOutlierEntry[]}
                    scoreKey="self_z_score"
                  />
                  <UserOutlierTable
                    title="Fastest Rising"
                    rows={activeMoodOutliers.fastest_rising as AggregateMoodOutlierEntry[]}
                    scoreKey="delta_1w"
                  />
                  <UserOutlierTable
                    title="Fastest Falling"
                    rows={activeMoodOutliers.fastest_falling as AggregateMoodOutlierEntry[]}
                    scoreKey="delta_1w"
                  />
                </>
              ) : (
                <>
                  <CohortOutlierTable
                    title="Most Elevated"
                    rows={activeMoodOutliers.most_elevated as AggregateCohortMoodOutlierEntry[]}
                    scoreKey="self_z_score"
                  />
                  <CohortOutlierTable
                    title="Most Depressed"
                    rows={activeMoodOutliers.most_depressed as AggregateCohortMoodOutlierEntry[]}
                    scoreKey="self_z_score"
                  />
                  <CohortOutlierTable
                    title="Fastest Rising"
                    rows={activeMoodOutliers.fastest_rising as AggregateCohortMoodOutlierEntry[]}
                    scoreKey="delta_1w"
                  />
                  <CohortOutlierTable
                    title="Fastest Falling"
                    rows={activeMoodOutliers.fastest_falling as AggregateCohortMoodOutlierEntry[]}
                    scoreKey="delta_1w"
                  />
                </>
              )}
            </div>
          </>
        ) : null}
      </article>
    </section>
  );
}

type UserOutlierTableProps = {
  title: string;
  rows: AggregateMoodOutlierEntry[];
  scoreKey: "self_z_score" | "delta_1w";
};

function UserOutlierTable({ title, rows, scoreKey }: UserOutlierTableProps) {
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

type CohortOutlierTableProps = {
  title: string;
  rows: AggregateCohortMoodOutlierEntry[];
  scoreKey: "self_z_score" | "delta_1w";
};

function CohortOutlierTable({ title, rows, scoreKey }: CohortOutlierTableProps) {
  return (
    <article className="panel mood-outlier-panel">
      <h3>{title}</h3>
      <div className="mood-outlier-table-wrap">
        <table className="mood-outlier-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Cohort</th>
              <th>Score</th>
              <th>Current</th>
              <th>1W</th>
              <th>Cohort Z</th>
              <th>Users</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="mood-outlier-empty">
                  No cohorts matched this ranking.
                </td>
              </tr>
            ) : (
              rows.map((row, index) => (
                <tr key={`${title}-${row.cohort_tag_slug ?? "all"}-${index}`}>
                  <td>{index + 1}</td>
                  <td>{row.cohort_tag_name}</td>
                  <td>{formatSignedValue(row[scoreKey])}</td>
                  <td>{formatValue(row.current_score)}</td>
                  <td>{formatSignedValue(row.delta_1w)}</td>
                  <td>{formatSignedValue(row.cohort_z_score)}</td>
                  <td>{integerFormatter.format(row.cohort_user_count)}</td>
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
