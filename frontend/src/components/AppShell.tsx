import type { ReactNode } from "react";

type AppShellProps = {
  activePage: "home" | "michael-saylor-vs-btc";
  onNavigate: (page: "home" | "michael-saylor-vs-btc") => void;
  children: ReactNode;
};

const navItems: Array<{
  key: "home" | "michael-saylor-vs-btc";
  label: string;
}> = [
  { key: "home", label: "Foundation" },
  { key: "michael-saylor-vs-btc", label: "Michael Saylor vs BTC" },
];

export function AppShell({ activePage, onNavigate, children }: AppShellProps) {
  const isDashboardPage = activePage === "michael-saylor-vs-btc";

  if (isDashboardPage) {
    return (
      <div className="app-dashboard-shell">
        <header className="dashboard-topbar">
          <div className="dashboard-topbar-brand">
            <span className="dashboard-topbar-kicker">Sentiment Analysis</span>
            <span className="dashboard-topbar-title">Michael Saylor vs BTC</span>
          </div>
          <nav className="dashboard-nav" aria-label="Primary">
            {navItems.map((item) => (
              <button
                key={item.key}
                className={`page-nav-link${activePage === item.key ? " is-active" : ""}`}
                onClick={() => onNavigate(item.key)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </nav>
        </header>
        <main className="dashboard-main">{children}</main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">Sentiment Analysis</p>
        <h1>Local-first X research foundation</h1>
        <p className="hero-copy">
          Backend ingestion and archival come first. The frontend stays lean
          until the data layer is trustworthy.
        </p>
        <nav className="page-nav" aria-label="Primary">
          {navItems.map((item) => (
            <button
              key={item.key}
              className={`page-nav-link${activePage === item.key ? " is-active" : ""}`}
              onClick={() => onNavigate(item.key)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
