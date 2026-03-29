import { useEffect, useRef, useState, type ReactNode } from "react";

import {
  type OverviewDefinition,
  getOverviewLabel,
} from "../config/overviews";

type AppShellProps = {
  mode: "home" | "dashboard";
  dashboardTitle?: string;
  activeOverviewSlug: string | null;
  overviews: OverviewDefinition[];
  onNavigateHome: () => void;
  onNavigateOverview: (slug: string) => void;
  children: ReactNode;
};

export function AppShell({
  mode,
  dashboardTitle,
  activeOverviewSlug,
  overviews,
  onNavigateHome,
  onNavigateOverview,
  children,
}: AppShellProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setIsDropdownOpen(false);
  }, [activeOverviewSlug, mode]);

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (!dropdownRef.current?.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }

    window.addEventListener("pointerdown", handlePointerDown);
    return () => {
      window.removeEventListener("pointerdown", handlePointerDown);
    };
  }, []);

  function renderNavigation(isDashboardNav: boolean) {
    return (
      <>
        <button
          className={`page-nav-link${activeOverviewSlug === null && mode === "home" ? " is-active" : ""}`}
          onClick={onNavigateHome}
          type="button"
        >
          Foundation
        </button>
        <div className="overview-dropdown" ref={dropdownRef}>
          <button
            aria-expanded={isDropdownOpen}
            className={`page-nav-link${activeOverviewSlug !== null ? " is-active" : ""}`}
            onClick={() => setIsDropdownOpen((current) => !current)}
            type="button"
          >
            Overviews
          </button>
          {isDropdownOpen ? (
            <div
              className={`overview-dropdown-menu${isDashboardNav ? " overview-dropdown-menu-dashboard" : ""}`}
              role="menu"
            >
              {overviews.map((overview) => (
                <button
                  key={overview.slug}
                  className={`overview-dropdown-item${activeOverviewSlug === overview.slug ? " is-active" : ""}`}
                  onClick={() => onNavigateOverview(overview.slug)}
                  role="menuitem"
                  type="button"
                >
                  {getOverviewLabel(overview)}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </>
    );
  }

  if (mode === "dashboard") {
    return (
      <div className="app-dashboard-shell">
        <header className="dashboard-topbar">
          <div className="dashboard-topbar-brand">
            <span className="dashboard-topbar-kicker">Sentiment Analysis</span>
            <span className="dashboard-topbar-title">{dashboardTitle ?? "Overview"}</span>
          </div>
          <nav className="dashboard-nav" aria-label="Primary">
            {renderNavigation(true)}
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
          {renderNavigation(false)}
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
