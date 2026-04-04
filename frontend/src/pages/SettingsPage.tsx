import { useState } from "react";

type ToggleCardProps = {
  title: string;
  description: string;
  value: boolean;
  onChange: () => void;
};

type SettingsPageProps = {
  showWatermark: boolean;
  onShowWatermarkChange: (value: boolean) => void;
};

const pendingMoves = [
  "Chart overlays and annotation defaults",
  "Per-dashboard layout preferences",
  "Data refresh behavior and stale-state handling",
  "Screenshot and export defaults",
];

export function SettingsPage({
  showWatermark,
  onShowWatermarkChange,
}: SettingsPageProps) {
  const [showAnnotations, setShowAnnotations] = useState(true);
  const [compactCards, setCompactCards] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  return (
    <section className="dashboard-page settings-page">
      <div className="content-stack">
        <article className="panel panel-accent settings-hero-card">
          <p className="eyebrow settings-eyebrow">Configuration</p>
          <div className="settings-hero-header">
            <div>
              <h1 className="settings-title">Settings and configuration</h1>
              <p className="status-copy settings-subtitle">
                Rough shell for controls that don&apos;t belong inside each dashboard. The
                switches below are placeholders for now, but the page structure is ready
                for real behavior to move in.
              </p>
            </div>
            <div className="settings-status-card">
              <span className="settings-status-label">Current phase</span>
              <strong>Scaffolded UI</strong>
              <p>Local-only state, no persistence yet.</p>
            </div>
          </div>
        </article>

        <section className="settings-grid">
          <article className="panel settings-section">
            <div className="settings-section-header">
              <div>
                <p className="chart-control-eyebrow">Display</p>
                <h2>Interface defaults</h2>
              </div>
              <p className="status-copy">Global settings that affect every dashboard.</p>
            </div>
            <div className="settings-toggle-list">
              <ToggleCard
                title="Show chart watermark"
                description="Applies everywhere. Turning this off removes the handle overlay from all chart dashboards."
                value={showWatermark}
                onChange={() => onShowWatermarkChange(!showWatermark)}
              />
              <ToggleCard
                title="Show annotations by default"
                description="Placeholder for chart notes, event markers, and other overlays."
                value={showAnnotations}
                onChange={() => setShowAnnotations((current) => !current)}
              />
              <ToggleCard
                title="Use compact metric cards"
                description="Reserved for tighter dashboard density once layout preferences move here."
                value={compactCards}
                onChange={() => setCompactCards((current) => !current)}
              />
            </div>
          </article>

          <article className="panel settings-section">
            <div className="settings-section-header">
              <div>
                <p className="chart-control-eyebrow">Data</p>
                <h2>Refresh and sync</h2>
              </div>
              <p className="status-copy">Rough inputs that can later bind to backend config.</p>
            </div>
            <div className="settings-toggle-list">
              <ToggleCard
                title="Auto-refresh dashboard data"
                description="Intended home for polling rules, background refresh cadence, and stale-data behavior."
                value={autoRefresh}
                onChange={() => setAutoRefresh((current) => !current)}
              />
            </div>
            <label className="settings-field">
              <span>Default landing dashboard</span>
              <select defaultValue="foundation">
                <option value="foundation">Foundation</option>
                <option value="bitcoin-mentions">Bitcoin mentions</option>
                <option value="overviews">Overviews</option>
                <option value="moods">Moods</option>
                <option value="heatmaps">Heat maps</option>
              </select>
            </label>
          </article>
        </section>

        <section className="settings-grid settings-grid-secondary">
          <article className="panel settings-section">
            <div className="settings-section-header">
              <div>
                <p className="chart-control-eyebrow">Roadmap</p>
                <h2>Good candidates to move here next</h2>
              </div>
            </div>
            <ul className="feature-list settings-feature-list">
              {pendingMoves.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className="panel settings-section">
            <div className="settings-section-header">
              <div>
                <p className="chart-control-eyebrow">Notes</p>
                <h2>Implementation posture</h2>
              </div>
            </div>
            <dl className="status-grid settings-status-grid">
              <div>
                <dt>Routing</dt>
                <dd>
                  Hash route at <code>#/settings</code>
                </dd>
              </div>
              <div>
                <dt>Entry point</dt>
                <dd>Gear action in the shared top-right shell</dd>
              </div>
              <div>
                <dt>State</dt>
                <dd>Watermark is app-global and persisted in local storage</dd>
              </div>
              <div>
                <dt>Next step</dt>
                <dd>Move one concrete dashboard preference into this page</dd>
              </div>
            </dl>
          </article>
        </section>
      </div>
    </section>
  );
}

function ToggleCard({ title, description, value, onChange }: ToggleCardProps) {
  return (
    <button
      aria-pressed={value}
      className={`settings-toggle-card${value ? " is-active" : ""}`}
      onClick={onChange}
      type="button"
    >
      <span className="settings-toggle-copy">
        <strong>{title}</strong>
        <span>{description}</span>
      </span>
      <span className={`settings-toggle-switch${value ? " is-active" : ""}`}>
        <span className="settings-toggle-knob" />
      </span>
    </button>
  );
}
