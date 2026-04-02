import { useEffect, useRef, useState, type ReactNode } from "react";

import {
  type HeatmapDefinition,
  getHeatmapLabel,
} from "../config/heatmaps";
import {
  type OverviewDefinition,
  getOverviewLabel,
} from "../config/overviews";

type AppShellProps = {
  mode: "home" | "dashboard";
  dashboardTitle?: string;
  activeOverviewSlug: string | null;
  activeHeatmapSlug: string | null;
  activeUtilityRoute: "bitcoin-mentions" | null;
  overviews: OverviewDefinition[];
  heatmaps: HeatmapDefinition[];
  onNavigateHome: () => void;
  onNavigateBitcoinMentions: () => void;
  onNavigateOverview: (slug: string) => void;
  onNavigateHeatmap: (slug: string) => void;
  children: ReactNode;
};

export function AppShell({
  mode,
  dashboardTitle,
  activeOverviewSlug,
  activeHeatmapSlug,
  activeUtilityRoute,
  overviews,
  heatmaps,
  onNavigateHome,
  onNavigateBitcoinMentions,
  onNavigateOverview,
  onNavigateHeatmap,
  children,
}: AppShellProps) {
  const [openMenu, setOpenMenu] = useState<"overviews" | "heatmaps" | null>(null);
  const navRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setOpenMenu(null);
  }, [activeHeatmapSlug, activeOverviewSlug, activeUtilityRoute, mode]);

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (!navRef.current?.contains(event.target as Node)) {
        setOpenMenu(null);
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
        <button
          className={`page-nav-link${activeUtilityRoute === "bitcoin-mentions" ? " is-active" : ""}`}
          onClick={onNavigateBitcoinMentions}
          type="button"
        >
          Bitcoin Mentions
        </button>
        <div className="overview-dropdown">
          <button
            aria-expanded={openMenu === "overviews"}
            className={`page-nav-link${activeOverviewSlug !== null ? " is-active" : ""}`}
            onClick={() =>
              setOpenMenu((current) => (current === "overviews" ? null : "overviews"))
            }
            type="button"
          >
            Overviews
          </button>
          {openMenu === "overviews" ? (
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
        <div className="overview-dropdown">
          <button
            aria-expanded={openMenu === "heatmaps"}
            className={`page-nav-link${activeHeatmapSlug !== null ? " is-active" : ""}`}
            onClick={() =>
              setOpenMenu((current) => (current === "heatmaps" ? null : "heatmaps"))
            }
            type="button"
          >
            Heat Maps
          </button>
          {openMenu === "heatmaps" ? (
            <div
              className={`overview-dropdown-menu${isDashboardNav ? " overview-dropdown-menu-dashboard" : ""}`}
              role="menu"
            >
              {heatmaps.map((heatmap) => (
                <button
                  key={heatmap.slug}
                  className={`overview-dropdown-item${activeHeatmapSlug === heatmap.slug ? " is-active" : ""}`}
                  onClick={() => onNavigateHeatmap(heatmap.slug)}
                  role="menuitem"
                  type="button"
                >
                  {getHeatmapLabel(heatmap)}
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
            <span className="dashboard-topbar-kicker">ChartProject</span>
            <span className="dashboard-topbar-title">{dashboardTitle ?? "Overview"}</span>
          </div>
          <nav className="dashboard-nav" aria-label="Primary" ref={navRef}>
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
        <p className="eyebrow">ChartProject</p>
        <h1>Local-first X research foundation</h1>
        <p className="hero-copy">
          Backend ingestion and archival come first. The frontend stays lean
          until the data layer is trustworthy.
        </p>
        <nav className="page-nav" aria-label="Primary" ref={navRef}>
          {renderNavigation(false)}
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
