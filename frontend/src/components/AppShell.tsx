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

  return (
    <div className={`app-shell${isDashboardPage ? " app-shell-wide app-shell-dashboard" : ""}`}>
      <header className={`hero${isDashboardPage ? " hero-compact" : ""}`}>
        <p className="eyebrow">Sentiment Analysis</p>
        {!isDashboardPage ? <h1>Local-first X research foundation</h1> : null}
        {!isDashboardPage ? (
          <p className="hero-copy">
            Backend ingestion and archival come first. The frontend stays lean
            until the data layer is trustworthy.
          </p>
        ) : null}
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
