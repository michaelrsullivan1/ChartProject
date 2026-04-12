import { themeDefinitions, type ThemeSlug } from "../lib/themes";

type ToggleCardProps = {
  title: string;
  description: string;
  value: boolean;
  onChange: () => void;
};

type SettingsPageProps = {
  theme: ThemeSlug;
  onThemeChange: (theme: ThemeSlug) => void;
  showWatermark: boolean;
  onShowWatermarkChange: (value: boolean) => void;
  anonymizeUsers: boolean;
  onAnonymizeUsersChange: (value: boolean) => void;
};

export function SettingsPage({
  theme,
  onThemeChange,
  showWatermark,
  onShowWatermarkChange,
  anonymizeUsers,
  onAnonymizeUsersChange,
}: SettingsPageProps) {
  return (
    <section className="dashboard-page settings-page">
      <div className="content-stack">
        <article className="panel panel-accent settings-hero-card">
          <p className="eyebrow settings-eyebrow">Configuration</p>
          <div className="settings-hero-header">
            <div>
              <h1 className="settings-title">Settings and configuration</h1>
              <p className="status-copy settings-subtitle">
                Configure global presentation and privacy defaults for every dashboard
                view in this workspace.
              </p>
            </div>
            <div className="settings-status-card">
              <span className="settings-status-label">Theme profile</span>
              <strong>{themeDefinitions.find((item) => item.slug === theme)?.label ?? "Slate Blue"}</strong>
              <p>All theme choices persist in local storage and apply instantly.</p>
            </div>
          </div>
        </article>

        <section className="settings-grid">
          <article className="panel settings-section">
            <div className="settings-section-header">
              <div>
                <p className="chart-control-eyebrow">Display</p>
                <h2>Global Defaults</h2>
              </div>
            </div>
            <div className="settings-theme-grid" role="radiogroup" aria-label="Theme">
              {themeDefinitions.map((themeOption) => {
                const isActive = themeOption.slug === theme;
                return (
                  <button
                    key={themeOption.slug}
                    aria-checked={isActive}
                    className={`settings-theme-card${isActive ? " is-active" : ""}`}
                    onClick={() => onThemeChange(themeOption.slug)}
                    role="radio"
                    type="button"
                  >
                    <span className="settings-theme-name">{themeOption.label}</span>
                    <span className="settings-theme-description">{themeOption.description}</span>
                  </button>
                );
              })}
            </div>
            <div className="settings-toggle-list">
              <ToggleCard
                title="Show chart watermark"
                description="Applies everywhere. Turning this off removes the handle overlay from all chart dashboards."
                value={showWatermark}
                onChange={() => onShowWatermarkChange(!showWatermark)}
              />
            </div>
          </article>

          <article className="panel settings-section">
            <div className="settings-section-header">
              <div>
                <p className="chart-control-eyebrow">Privacy</p>
                <h2>Anonymize Users</h2>
              </div>
            </div>
            <div className="settings-toggle-list">
              <ToggleCard
                title="Anonymize user names"
                description="Prepares the dashboard to swap visible accounts for labels like Anonymous 1 and Anonymous 2 when enabled."
                value={anonymizeUsers}
                onChange={() => onAnonymizeUsersChange(!anonymizeUsers)}
              />
            </div>
          </article>
        </section>

        <article className="panel settings-section settings-section-full">
          <div className="settings-section-header">
            <div>
              <p className="chart-control-eyebrow">Mood Configuration</p>
              <h2>Mood Configuration</h2>
            </div>
          </div>
          <div className="settings-mood-placeholder">
            <div className="settings-mood-placeholder-panel">
              <p className="settings-mood-placeholder-title">No per-user mood controls configured yet</p>
              <p className="settings-mood-placeholder-copy">
                Future controls here should let you pick a user, then hide or reveal individual
                mood options from that user&apos;s sidebar without affecting everyone else.
              </p>
            </div>
          </div>
        </article>
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
