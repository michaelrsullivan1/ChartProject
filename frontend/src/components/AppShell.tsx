import { useEffect, useRef, useState, type ReactNode } from "react";

import {
  type AggregateMoodDefinition,
  getAggregateMoodLabel,
} from "../config/aggregateMoods";
import {
  type BitcoinMentionsDefinition,
  getBitcoinMentionsLabel,
} from "../lib/authorDefinitions";
import {
  type HeatmapDefinition,
  getHeatmapLabel,
} from "../lib/authorDefinitions";
import {
  type MoodDefinition,
  getMoodLabel,
} from "../lib/authorDefinitions";
import {
  type OverviewDefinition,
  getOverviewLabel,
} from "../lib/authorDefinitions";

type AppShellProps = {
  mode: "home" | "dashboard";
  dashboardTitle?: string;
  activeUserPodcastView?: "narrative-mix" | "narrative-intensity" | "beliefs" | null;
  activePodcastPersonSlug: string | null;
  activeBitcoinMentionsSlug: string | null;
  activeAggregateMoodSlug: string | null;
  activeAggregateNarratives: boolean;
  activeMoodOutliers?: boolean;
  activePriceMentions?: boolean;
  activeMoodSlug: string | null;
  activeOverviewSlug: string | null;
  activeHeatmapSlug: string | null;
  activeSettingsSection: "global" | "user" | null;
  aggregateMoods: AggregateMoodDefinition[];
  bitcoinMentions: BitcoinMentionsDefinition[];
  moods: MoodDefinition[];
  overviews: OverviewDefinition[];
  heatmaps: HeatmapDefinition[];
  onNavigateHome: () => void;
  onNavigatePodcastPerson: (slug: string) => void;
  onNavigateAggregateMood: (slug: string) => void;
  onNavigateAggregateNarratives: () => void;
  onNavigateMoodOutliers?: () => void;
  onNavigateBitcoinMentions: (slug: string) => void;
  onNavigateMood: (slug: string) => void;
  onNavigateOverview: (slug: string) => void;
  onNavigateHeatmap: (slug: string) => void;
  onNavigateGlobalSettings: () => void;
  onNavigateUserSettings: () => void;
  children: ReactNode;
};

export function AppShell({
  mode,
  dashboardTitle,
  activeUserPodcastView = null,
  activePodcastPersonSlug,
  activeBitcoinMentionsSlug,
  activeAggregateMoodSlug,
  activeAggregateNarratives,
  activeMoodOutliers = false,
  activePriceMentions = false,
  activeMoodSlug,
  activeOverviewSlug,
  activeHeatmapSlug,
  activeSettingsSection,
  aggregateMoods,
  bitcoinMentions,
  moods,
  overviews,
  heatmaps,
  onNavigateHome,
  onNavigatePodcastPerson,
  onNavigateAggregateMood,
  onNavigateAggregateNarratives,
  onNavigateMoodOutliers = () => {
    window.location.hash = "#/mood-outliers";
  },
  onNavigateBitcoinMentions,
  onNavigateMood,
  onNavigateOverview,
  onNavigateHeatmap,
  onNavigateGlobalSettings,
  onNavigateUserSettings,
  children,
}: AppShellProps) {
  const podcastUsers = [{ slug: "michael-saylor", label: "Michael Saylor" }] as const;
  const [openMenu, setOpenMenu] = useState<
    | "user-narrative-mix"
    | "user-narrative-intensity"
    | "user-beliefs"
    | "aggregate-moods"
    | "bitcoin-mentions"
    | "moods"
    | "overviews"
    | "heatmaps"
    | "settings"
    | null
  >(null);
  const navRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setOpenMenu(null);
  }, [
    activeUserPodcastView,
    activeAggregateMoodSlug,
    activeAggregateNarratives,
    activeMoodOutliers,
    activePriceMentions,
    activeBitcoinMentionsSlug,
    activeHeatmapSlug,
    activeMoodSlug,
    activePodcastPersonSlug,
    activeOverviewSlug,
    activeSettingsSection,
    mode,
  ]);

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

  function navigateToGlobalSettings() {
    setOpenMenu(null);
    onNavigateGlobalSettings();
  }

  function navigateToUserSettings() {
    setOpenMenu(null);
    onNavigateUserSettings();
  }

  function navigateToUserPodcastView(
    view: "narrative-mix" | "narrative-intensity" | "beliefs",
    personSlug: string,
  ) {
    setOpenMenu(null);
    window.location.hash = `#/user-${view}/${encodeURIComponent(personSlug)}`;
  }

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
            aria-expanded={openMenu === "user-narrative-mix"}
            className={`page-nav-link${activeUserPodcastView === "narrative-mix" ? " is-active" : ""}`}
            onClick={() =>
              setOpenMenu((current) =>
                current === "user-narrative-mix" ? null : "user-narrative-mix",
              )
            }
            type="button"
          >
            User Narrative Mix
          </button>
          {openMenu === "user-narrative-mix" ? (
            <div
              className={`overview-dropdown-menu${isDashboardNav ? " overview-dropdown-menu-dashboard" : ""}`}
              role="menu"
            >
              {podcastUsers.map((user) => (
                <button
                  key={user.slug}
                  className={`overview-dropdown-item${activeUserPodcastView === "narrative-mix" && activePodcastPersonSlug === user.slug ? " is-active" : ""}`}
                  onClick={() => navigateToUserPodcastView("narrative-mix", user.slug)}
                  role="menuitem"
                  type="button"
                >
                  {user.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <div className="overview-dropdown">
          <button
            aria-expanded={openMenu === "user-narrative-intensity"}
            className={`page-nav-link${activeUserPodcastView === "narrative-intensity" ? " is-active" : ""}`}
            onClick={() =>
              setOpenMenu((current) =>
                current === "user-narrative-intensity" ? null : "user-narrative-intensity",
              )
            }
            type="button"
          >
            User Narrative Intensity
          </button>
          {openMenu === "user-narrative-intensity" ? (
            <div
              className={`overview-dropdown-menu${isDashboardNav ? " overview-dropdown-menu-dashboard" : ""}`}
              role="menu"
            >
              {podcastUsers.map((user) => (
                <button
                  key={user.slug}
                  className={`overview-dropdown-item${activeUserPodcastView === "narrative-intensity" && activePodcastPersonSlug === user.slug ? " is-active" : ""}`}
                  onClick={() => navigateToUserPodcastView("narrative-intensity", user.slug)}
                  role="menuitem"
                  type="button"
                >
                  {user.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <div className="overview-dropdown">
          <button
            aria-expanded={openMenu === "user-beliefs"}
            className={`page-nav-link${activeUserPodcastView === "beliefs" ? " is-active" : ""}`}
            onClick={() =>
              setOpenMenu((current) => (current === "user-beliefs" ? null : "user-beliefs"))
            }
            type="button"
          >
            User Beliefs
          </button>
          {openMenu === "user-beliefs" ? (
            <div
              className={`overview-dropdown-menu${isDashboardNav ? " overview-dropdown-menu-dashboard" : ""}`}
              role="menu"
            >
              {podcastUsers.map((user) => (
                <button
                  key={user.slug}
                  className={`overview-dropdown-item${activeUserPodcastView === "beliefs" && activePodcastPersonSlug === user.slug ? " is-active" : ""}`}
                  onClick={() => navigateToUserPodcastView("beliefs", user.slug)}
                  role="menuitem"
                  type="button"
                >
                  {user.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
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
            User Moods
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
            aria-expanded={openMenu === "aggregate-moods"}
            className={`page-nav-link${activeAggregateMoodSlug !== null ? " is-active" : ""}`}
            onClick={() =>
              setOpenMenu((current) =>
                current === "aggregate-moods" ? null : "aggregate-moods",
              )
            }
            type="button"
          >
            Aggregate Moods
          </button>
          {openMenu === "aggregate-moods" ? (
            <div
              className={`overview-dropdown-menu${isDashboardNav ? " overview-dropdown-menu-dashboard" : ""}`}
              role="menu"
            >
              {aggregateMoods.map((aggregateMood) => (
                <button
                  key={aggregateMood.slug}
                  className={`overview-dropdown-item${activeAggregateMoodSlug === aggregateMood.slug ? " is-active" : ""}`}
                  onClick={() => onNavigateAggregateMood(aggregateMood.slug)}
                  role="menuitem"
                  type="button"
                >
                  {getAggregateMoodLabel(aggregateMood)}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <button
          className={`page-nav-link${activeAggregateNarratives ? " is-active" : ""}`}
          onClick={onNavigateAggregateNarratives}
          type="button"
        >
          Aggregate Narratives
        </button>
        <button
          className={`page-nav-link${activeMoodOutliers ? " is-active" : ""}`}
          onClick={onNavigateMoodOutliers}
          type="button"
        >
          Mood Outliers
        </button>
        <button
          className={`page-nav-link${activePriceMentions ? " is-active" : ""}`}
          onClick={() => { window.location.hash = "#/price-mentions"; }}
          type="button"
        >
          Price Mentions
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
            User Narratives
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

  function renderSettingsMenu() {
    return (
      <div className="overview-dropdown settings-dropdown">
        <button
          aria-expanded={openMenu === "settings"}
          aria-label="Open settings"
          className={`page-nav-link page-nav-icon-link${activeSettingsSection !== null ? " is-active" : ""}`}
          onClick={() => setOpenMenu((current) => (current === "settings" ? null : "settings"))}
          type="button"
        >
          <SettingsIcon />
        </button>
        {openMenu === "settings" ? (
          <div
            className="overview-dropdown-menu overview-dropdown-menu-dashboard settings-dropdown-menu"
            onPointerDown={(event) => event.stopPropagation()}
            role="menu"
          >
            <button
              className={`overview-dropdown-item${activeSettingsSection === "global" ? " is-active" : ""}`}
              onClick={navigateToGlobalSettings}
              role="menuitem"
              type="button"
            >
              Global Settings
            </button>
            <button
              className={`overview-dropdown-item${activeSettingsSection === "user" ? " is-active" : ""}`}
              onClick={navigateToUserSettings}
              role="menuitem"
              type="button"
            >
              User Settings
            </button>
          </div>
        ) : null}
      </div>
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
          <div className="topbar-actions" ref={navRef}>
            <nav className="dashboard-nav" aria-label="Primary">
              {renderNavigation(true)}
            </nav>
            {renderSettingsMenu()}
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
        <div className="hero-nav-row" ref={navRef}>
          <nav className="page-nav" aria-label="Primary">
            {renderNavigation(false)}
          </nav>
          {renderSettingsMenu()}
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}

function SettingsIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.82-.34 1.7 1.7 0 0 0-1 1.52V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1-1.52 1.7 1.7 0 0 0-1.82.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.82 1.7 1.7 0 0 0-1.52-1H3a2 2 0 1 1 0-4h.09a1.7 1.7 0 0 0 1.52-1 1.7 1.7 0 0 0-.34-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.82.34h.18a1.7 1.7 0 0 0 1-1.52V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.52 1.7 1.7 0 0 0 1.82-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.82v.18a1.7 1.7 0 0 0 1.52 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.52 1z" />
    </svg>
  );
}
