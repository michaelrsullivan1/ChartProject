export function UserSettingsPage() {
  return (
    <section className="dashboard-page settings-page">
      <article className="panel panel-accent settings-hero-card">
        <p className="eyebrow settings-eyebrow">Configuration</p>
        <div className="settings-hero-header">
          <div>
            <h1 className="settings-title">User settings</h1>
            <p className="status-copy settings-subtitle">
              User-specific settings are split into their own route and will be configured here.
            </p>
          </div>
          <div className="settings-status-card">
            <span className="settings-status-label">Current phase</span>
            <strong>Placeholder</strong>
            <p>No user-specific toggles are configured yet.</p>
          </div>
        </div>
      </article>
    </section>
  );
}
