import { useEffect, useRef, useState, type ReactNode } from "react";

import {
  type BitcoinMentionsDefinition,
  getBitcoinMentionsLabel,
} from "../config/bitcoinMentions";
import {
  type HeatmapDefinition,
  getHeatmapLabel,
} from "../config/heatmaps";
import {
  type MoodDefinition,
  getMoodLabel,
} from "../config/moods";
import {
  type OverviewDefinition,
  getOverviewLabel,
} from "../config/overviews";

type AppShellProps = {
  mode: "home" | "dashboard";
  dashboardTitle?: string;
  activeBitcoinMentionsSlug: string | null;
  activeMoodSlug: string | null;
  activeOverviewSlug: string | null;
  activeHeatmapSlug: string | null;
  bitcoinMentions: BitcoinMentionsDefinition[];
  moods: MoodDefinition[];
  overviews: OverviewDefinition[];
  heatmaps: HeatmapDefinition[];
  onNavigateHome: () => void;
  onNavigateBitcoinMentions: (slug: string) => void;
  onNavigateMood: (slug: string) => void;
  onNavigateOverview: (slug: string) => void;
  onNavigateHeatmap: (slug: string) => void;
  onNavigateSettings: () => void;
  isSettingsActive: boolean;
  children: ReactNode;
};

export function AppShell({
  mode,
  dashboardTitle,
  activeBitcoinMentionsSlug,
  activeMoodSlug,
  activeOverviewSlug,
  activeHeatmapSlug,
  bitcoinMentions,
  moods,
  overviews,
  heatmaps,
  onNavigateHome,
  onNavigateBitcoinMentions,
  onNavigateMood,
  onNavigateOverview,
  onNavigateHeatmap,
  onNavigateSettings,
  isSettingsActive,
  children,
}: AppShellProps) {
  const [openMenu, setOpenMenu] = useState<"bitcoin-mentions" | "moods" | "overviews" | "heatmaps" | null>(null);
  const navRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setOpenMenu(null);
  }, [activeBitcoinMentionsSlug, activeHeatmapSlug, activeMoodSlug, activeOverviewSlug, mode]);

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
        <div className="overview-dropdown">
          <button
            aria-expanded={openMenu === "bitcoin-mentions"}
            className={`page-nav-link${activeBitcoinMentionsSlug !== null ? " is-active" : ""}`}
            onClick={() =>
              setOpenMenu((current) => (current === "bitcoin-mentions" ? null : "bitcoin-mentions"))
            }
            type="button"
          >
            Bitcoin Mentions
          </button>
          {openMenu === "bitcoin-mentions" ? (
            <div
              className={`overview-dropdown-menu${isDashboardNav ? " overview-dropdown-menu-dashboard" : ""}`}
              role="menu"
            >
              {bitcoinMentions.map((definition) => (
                <button
                  key={definition.slug}
                  className={`overview-dropdown-item${activeBitcoinMentionsSlug === definition.slug ? " is-active" : ""}`}
                  onClick={() => onNavigateBitcoinMentions(definition.slug)}
                  role="menuitem"
                  type="button"
                >
                  {getBitcoinMentionsLabel(definition)}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <div className="overview-dropdown">
          <button
            aria-expanded={openMenu === "moods"}
            className={`page-nav-link${activeMoodSlug !== null ? " is-active" : ""}`}
            onClick={() => setOpenMenu((current) => (current === "moods" ? null : "moods"))}
            type="button"
          >
            Moods
          </button>
          {openMenu === "moods" ? (
            <div
              className={`overview-dropdown-menu${isDashboardNav ? " overview-dropdown-menu-dashboard" : ""}`}
              role="menu"
            >
              {moods.map((mood) => (
                <button
                  key={mood.slug}
                  className={`overview-dropdown-item${activeMoodSlug === mood.slug ? " is-active" : ""}`}
                  onClick={() => onNavigateMood(mood.slug)}
                  role="menuitem"
                  type="button"
                >
                  {getMoodLabel(mood)}
                </button>
              ))}
            </div>
          ) : null}
        </div>
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
            <span className="dashboard-topbar-kicker">Sentiment And Mood Analysis</span>
            <span className="dashboard-topbar-title">{dashboardTitle ?? "Overview"}</span>
          </div>
          <div className="topbar-actions">
            <nav className="dashboard-nav" aria-label="Primary" ref={navRef}>
              {renderNavigation(true)}
            </nav>
            <button
              aria-label="Open settings"
              className={`page-nav-link page-nav-icon-link${isSettingsActive ? " is-active" : ""}`}
              onClick={onNavigateSettings}
              type="button"
            >
              <SettingsIcon />
            </button>
          </div>
        </header>
        <main className="dashboard-main">{children}</main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">Sentiment And Mood Analysis</p>
        <h1>Local-first X research foundation</h1>
        <p className="hero-copy">
          Backend ingestion and archival come first. The frontend stays lean
          until the data layer is trustworthy.
        </p>
        <div className="hero-nav-row">
          <nav className="page-nav" aria-label="Primary" ref={navRef}>
            {renderNavigation(false)}
          </nav>
          <button
            aria-label="Open settings"
            className={`page-nav-link page-nav-icon-link${isSettingsActive ? " is-active" : ""}`}
            onClick={onNavigateSettings}
            type="button"
          >
            <SettingsIcon />
          </button>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}

function SettingsIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M10.5 3.3h3l.8 2.3a6.9 6.9 0 0 1 1.6.9l2.3-.8 1.5 2.6-1.6 1.8a6 6 0 0 1 0 1.9l1.6 1.8-1.5 2.6-2.3-.8a6.9 6.9 0 0 1-1.6.9l-.8 2.3h-3l-.8-2.3a6.9 6.9 0 0 1-1.6-.9l-2.3.8-1.5-2.6 1.6-1.8a6 6 0 0 1 0-1.9L4.1 8.4l1.5-2.6 2.3.8a6.9 6.9 0 0 1 1.6-.9l1-2.4Z" />
      <circle cx="12" cy="12" r="3.1" />
    </svg>
  );
}
