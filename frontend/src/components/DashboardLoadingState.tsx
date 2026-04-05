export function DashboardLoadingState() {
  return (
    <div className="dashboard-loading-state" role="status" aria-live="polite" aria-label="Refreshing view">
      <span className="dashboard-loading-spinner" aria-hidden="true" />
    </div>
  );
}
