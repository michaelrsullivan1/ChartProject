import { useEffect, useState } from "react";

import { fetchAuthorRegistry } from "./api/authorRegistry";
import { fetchHealth } from "./api/health";
import { AppShell } from "./components/AppShell";
import { DashboardLoadingState } from "./components/DashboardLoadingState";
import {
  aggregateMoodDefinitions,
  findAggregateMoodBySlug,
  getAggregateMoodHash,
  getAggregateMoodTitle,
  type AggregateMoodDefinition,
} from "./config/aggregateMoods";
import {
  getBitcoinMentionsLabel,
  getBitcoinMentionsHash,
  getBitcoinMentionsTitle,
  type BitcoinMentionsDefinition,
} from "./lib/authorDefinitions";
import {
  getHeatmapHash,
  getHeatmapLabel,
  getHeatmapTitle,
  type HeatmapDefinition,
} from "./lib/authorDefinitions";
import {
  getMoodLabel,
  getMoodHash,
  getMoodTitle,
  type MoodDefinition,
} from "./lib/authorDefinitions";
import {
  getOverviewLabel,
  getOverviewHash,
  getOverviewTitle,
  type OverviewDefinition,
} from "./lib/authorDefinitions";
import { HomePage } from "./pages/HomePage";
import { AuthorHeatmapPage } from "./pages/AuthorHeatmapPage";
import { AuthorMoodPage } from "./pages/AuthorMoodPage";
import { AggregateMoodPage } from "./pages/AggregateMoodPage";
import { AggregateNarrativesPage } from "./pages/AggregateNarrativesPage";
import { MoodOutliersPage } from "./pages/MoodOutliersPage";
import { BitcoinMentionsPage } from "./pages/BitcoinMentionsPage";
import { AuthorOverviewPage } from "./pages/MichaelSaylorVsBtcPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PodcastPersonPage } from "./pages/PodcastPersonPage";
import { PriceMentionsPage } from "./pages/PriceMentionsPage";
import { PriceMentionDistributionPage } from "./pages/PriceMentionDistributionPage";
import { PriceMentionZScorePage } from "./pages/PriceMentionZScorePage";
import { UserBeliefsPage } from "./pages/UserBeliefsPage";
import { UserNarrativeIntensityPage } from "./pages/UserNarrativeIntensityPage";
import { UserNarrativeMixPage } from "./pages/UserNarrativeMixPage";
import { SettingsPage } from "./pages/SettingsPage";
import { UserSettingsPage } from "./pages/UserSettingsPage";
import {
  ANONYMIZE_USERS_STORAGE_KEY,
  CHART_WATERMARK_STORAGE_KEY,
  THEME_STORAGE_KEY,
} from "./lib/settings";
import { isThemeSlug, type ThemeSlug } from "./lib/themes";
import type { HealthResponse } from "./types/health";

type AppRoute =
  | { kind: "home" }
  | { kind: "podcast-person"; personSlug: string }
  | { kind: "user-narrative-mix"; personSlug: string }
  | { kind: "user-narrative-intensity"; personSlug: string }
  | { kind: "user-beliefs"; personSlug: string }
  | { kind: "aggregate-mood"; aggregateMood: AggregateMoodDefinition }
  | { kind: "aggregate-narratives" }
  | { kind: "mood-outliers" }
  | { kind: "price-mentions"; view: "heatmap" | "distribution" | "zscore" }
  | { kind: "bitcoin-mentions"; bitcoinMentions: BitcoinMentionsDefinition }
  | { kind: "mood"; mood: MoodDefinition }
  | { kind: "overview"; overview: OverviewDefinition }
  | { kind: "heatmap"; heatmap: HeatmapDefinition }
  | { kind: "settings"; section: "global" | "user" }
  | { kind: "not-found" };

type RouteDefinitions = {
  bitcoinMentions: BitcoinMentionsDefinition[];
  moods: MoodDefinition[];
  overviews: OverviewDefinition[];
  heatmaps: HeatmapDefinition[];
};

function findBySlug<T extends { slug: string }>(definitions: T[], slug: string): T | undefined {
  return definitions.find((definition) => definition.slug === slug);
}

function getHashPath(hash: string): string {
  const queryIndex = hash.indexOf("?");
  return queryIndex >= 0 ? hash.slice(0, queryIndex) : hash;
}

function isRegistryBackedHash(hash: string): boolean {
  const path = getHashPath(hash);
  return (
    path === "#/bitcoin-mentions" ||
    path === "#/narratives" ||
    path === "#/heatmaps" ||
    path.startsWith("#/bitcoin-mentions/") ||
    path.startsWith("#/overviews/") ||
    path.startsWith("#/moods/") ||
    path.startsWith("#/narratives/") ||
    path.startsWith("#/heatmaps/")
  );
}

function getRouteFromHash(hash: string, definitions: RouteDefinitions): AppRoute {
  const path = getHashPath(hash);

  if (path === "" || path === "#" || path === "#/") {
    return { kind: "home" };
  }

  if (path.startsWith("#/podcasts/")) {
    const personSlug = decodeURIComponent(path.slice("#/podcasts/".length));
    return personSlug ? { kind: "podcast-person", personSlug } : { kind: "not-found" };
  }

  if (path === "#/user-narrative-mix") {
    return { kind: "user-narrative-mix", personSlug: "michael-saylor" };
  }

  if (path.startsWith("#/user-narrative-mix/")) {
    const personSlug = decodeURIComponent(path.slice("#/user-narrative-mix/".length));
    return personSlug ? { kind: "user-narrative-mix", personSlug } : { kind: "not-found" };
  }

  if (path === "#/user-narrative-intensity") {
    return { kind: "user-narrative-intensity", personSlug: "michael-saylor" };
  }

  if (path.startsWith("#/user-narrative-intensity/")) {
    const personSlug = decodeURIComponent(path.slice("#/user-narrative-intensity/".length));
    return personSlug ? { kind: "user-narrative-intensity", personSlug } : { kind: "not-found" };
  }

  if (path === "#/user-beliefs") {
    return { kind: "user-beliefs", personSlug: "michael-saylor" };
  }

  if (path.startsWith("#/user-beliefs/")) {
    const personSlug = decodeURIComponent(path.slice("#/user-beliefs/".length));
    return personSlug ? { kind: "user-beliefs", personSlug } : { kind: "not-found" };
  }

  if (path === "#/bitcoin-mentions") {
    const bitcoinMentions = definitions.bitcoinMentions[0];
    return bitcoinMentions ? { kind: "bitcoin-mentions", bitcoinMentions } : { kind: "not-found" };
  }

  if (path === "#/aggregate-moods") {
    const aggregateMood = aggregateMoodDefinitions[0];
    return aggregateMood ? { kind: "aggregate-mood", aggregateMood } : { kind: "not-found" };
  }

  if (path === "#/aggregate-narratives") {
    return { kind: "aggregate-narratives" };
  }

  if (path === "#/mood-outliers") {
    return { kind: "mood-outliers" };
  }

  if (path === "#/price-mentions" || path === "#/price-mentions/heatmap") {
    return { kind: "price-mentions", view: "heatmap" };
  }

  if (path === "#/price-mentions/distribution") {
    return { kind: "price-mentions", view: "distribution" };
  }

  if (path === "#/price-mentions/zscore") {
    return { kind: "price-mentions", view: "zscore" };
  }

  if (path.startsWith("#/bitcoin-mentions/")) {
    const slug = decodeURIComponent(path.slice("#/bitcoin-mentions/".length));
    const bitcoinMentions = findBySlug(definitions.bitcoinMentions, slug);
    return bitcoinMentions ? { kind: "bitcoin-mentions", bitcoinMentions } : { kind: "not-found" };
  }

  if (path.startsWith("#/aggregate-moods/")) {
    const slug = decodeURIComponent(path.slice("#/aggregate-moods/".length));
    const aggregateMood = findAggregateMoodBySlug(slug);
    return aggregateMood ? { kind: "aggregate-mood", aggregateMood } : { kind: "not-found" };
  }

  if (path.startsWith("#/overviews/")) {
    const slug = decodeURIComponent(path.slice("#/overviews/".length));
    const overview = findBySlug(definitions.overviews, slug);
    return overview ? { kind: "overview", overview } : { kind: "not-found" };
  }

  if (path.startsWith("#/moods/")) {
    const slug = decodeURIComponent(path.slice("#/moods/".length));
    const mood = findBySlug(definitions.moods, slug);
    return mood ? { kind: "mood", mood } : { kind: "not-found" };
  }

  if (path === "#/narratives" || path === "#/heatmaps") {
    const heatmap = definitions.heatmaps[0];
    return heatmap ? { kind: "heatmap", heatmap } : { kind: "not-found" };
  }

  if (path.startsWith("#/narratives/")) {
    const slug = decodeURIComponent(path.slice("#/narratives/".length));
    const heatmap = findBySlug(definitions.heatmaps, slug);
    return heatmap ? { kind: "heatmap", heatmap } : { kind: "not-found" };
  }

  if (path.startsWith("#/heatmaps/")) {
    const slug = decodeURIComponent(path.slice("#/heatmaps/".length));
    const heatmap = findBySlug(definitions.heatmaps, slug);
    return heatmap ? { kind: "heatmap", heatmap } : { kind: "not-found" };
  }

  if (path === "#/settings") {
    return { kind: "settings", section: "global" };
  }

  if (path === "#/settings/global-settings") {
    return { kind: "settings", section: "global" };
  }

  if (path === "#/settings/user-settings") {
    return { kind: "settings", section: "user" };
  }

  return { kind: "not-found" };
}

function sortDefinitionsByLabel<T extends { slug: string }>(
  definitions: T[],
  getLabel: (definition: T) => string,
): T[] {
  return [...definitions].sort((left, right) => {
    const labelComparison = getLabel(left).localeCompare(getLabel(right), undefined, {
      sensitivity: "base",
    });
    if (labelComparison !== 0) {
      return labelComparison;
    }

    return left.slug.localeCompare(right.slug, undefined, { sensitivity: "base" });
  });
}

export default function App() {
  const [bitcoinMentionsDefinitions, setBitcoinMentionsDefinitions] = useState<BitcoinMentionsDefinition[]>([]);
  const [moodDefinitions, setMoodDefinitions] = useState<MoodDefinition[]>([]);
  const [overviewDefinitions, setOverviewDefinitions] = useState<OverviewDefinition[]>([]);
  const [heatmapDefinitions, setHeatmapDefinitions] = useState<HeatmapDefinition[]>([]);
  const [isAuthorRegistryLoading, setIsAuthorRegistryLoading] = useState(true);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [route, setRoute] = useState<AppRoute>(() =>
    getRouteFromHash(window.location.hash, {
      bitcoinMentions: sortDefinitionsByLabel([], getBitcoinMentionsLabel),
      moods: sortDefinitionsByLabel([], getMoodLabel),
      overviews: sortDefinitionsByLabel([], getOverviewLabel),
      heatmaps: sortDefinitionsByLabel([], getHeatmapLabel),
    }),
  );
  const [showWatermark, setShowWatermark] = useState(() => {
    const storedValue = window.localStorage.getItem(CHART_WATERMARK_STORAGE_KEY);
    return storedValue === null ? true : storedValue === "true";
  });
  const [anonymizeUsers, setAnonymizeUsers] = useState(() => {
    const storedValue = window.localStorage.getItem(ANONYMIZE_USERS_STORAGE_KEY);
    return storedValue === null ? false : storedValue === "true";
  });
  const [theme, setTheme] = useState<ThemeSlug>(() => {
    const storedValue = window.localStorage.getItem(THEME_STORAGE_KEY);
    const resolvedTheme = storedValue !== null && isThemeSlug(storedValue) ? storedValue : "slate";
    document.documentElement.dataset.theme = resolvedTheme;
    return resolvedTheme;
  });
  const sortedBitcoinMentionsDefinitions = sortDefinitionsByLabel(
    bitcoinMentionsDefinitions,
    getBitcoinMentionsLabel,
  );
  const sortedMoodDefinitions = sortDefinitionsByLabel(moodDefinitions, getMoodLabel);
  const sortedOverviewDefinitions = sortDefinitionsByLabel(
    overviewDefinitions,
    getOverviewLabel,
  );
  const sortedHeatmapDefinitions = sortDefinitionsByLabel(heatmapDefinitions, getHeatmapLabel);

  useEffect(() => {
    let cancelled = false;

    async function loadHealth() {
      try {
        const response = await fetchHealth();
        console.info("ChartProject health check succeeded", response);
        if (!cancelled) {
          setHealth(response);
          setError(null);
        }
      } catch (loadError) {
        console.error("ChartProject health check failed", loadError);
        if (!cancelled) {
          setError(
            loadError instanceof Error ? loadError.message : "Unknown health check failure",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadHealth();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadAuthorRegistry() {
      try {
        const registry = await fetchAuthorRegistry();
        if (cancelled) {
          return;
        }
        setOverviewDefinitions(
          registry.overviews.map((item) => ({
            slug: item.slug,
            username: item.username,
            apiBasePath: item.api_base_path,
          })),
        );
        setMoodDefinitions(
          registry.moods.map((item) => ({
            slug: item.slug,
            username: item.username,
            apiBasePath: item.api_base_path,
          })),
        );
        setHeatmapDefinitions(
          registry.heatmaps.map((item) => ({
            slug: item.slug,
            username: item.username,
            apiBasePath: item.api_base_path,
          })),
        );
        setBitcoinMentionsDefinitions(
          registry.bitcoin_mentions.map((item) => ({
            slug: item.slug,
            username: item.username,
            apiBasePath: item.api_base_path,
          })),
        );
      } catch (loadError) {
        console.warn("ChartProject author registry request failed", loadError);
      } finally {
        if (!cancelled) {
          setIsAuthorRegistryLoading(false);
        }
      }
    }

    void loadAuthorRegistry();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function handleHashChange() {
      const currentBitcoinMentionsDefinitions = sortDefinitionsByLabel(
        bitcoinMentionsDefinitions,
        getBitcoinMentionsLabel,
      );
      const currentMoodDefinitions = sortDefinitionsByLabel(moodDefinitions, getMoodLabel);
      const currentOverviewDefinitions = sortDefinitionsByLabel(
        overviewDefinitions,
        getOverviewLabel,
      );
      const currentHeatmapDefinitions = sortDefinitionsByLabel(
        heatmapDefinitions,
        getHeatmapLabel,
      );

      setRoute(
        getRouteFromHash(window.location.hash, {
          bitcoinMentions: currentBitcoinMentionsDefinitions,
          moods: currentMoodDefinitions,
          overviews: currentOverviewDefinitions,
          heatmaps: currentHeatmapDefinitions,
        }),
      );
    }

    handleHashChange();
    window.addEventListener("hashchange", handleHashChange);
    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, [bitcoinMentionsDefinitions, moodDefinitions, overviewDefinitions, heatmapDefinitions]);

  useEffect(() => {
    window.localStorage.setItem(CHART_WATERMARK_STORAGE_KEY, String(showWatermark));
  }, [showWatermark]);

  useEffect(() => {
    window.localStorage.setItem(ANONYMIZE_USERS_STORAGE_KEY, String(anonymizeUsers));
  }, [anonymizeUsers]);

  useEffect(() => {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  function navigateHome() {
    window.location.hash = "#/";
  }

  function navigateOverview(slug: string) {
    window.location.hash = getOverviewHash(slug);
  }

  function navigatePodcastPerson(slug: string) {
    window.location.hash = `#/podcasts/${encodeURIComponent(slug)}`;
  }

  function navigateAggregateMood(slug: string) {
    window.location.hash = getAggregateMoodHash(slug);
  }

  function navigateAggregateNarratives() {
    window.location.hash = "#/aggregate-narratives";
  }

  function navigateMoodOutliers() {
    window.location.hash = "#/mood-outliers";
  }

  function navigateMood(slug: string) {
    window.location.hash = getMoodHash(slug);
  }

  function navigateBitcoinMentions(slug: string) {
    window.location.hash = getBitcoinMentionsHash(slug);
  }

  function navigateHeatmap(slug: string) {
    window.location.hash = getHeatmapHash(slug);
  }

  function navigateGlobalSettings() {
    window.location.hash = "#/settings/global-settings";
  }

  function navigateUserSettings() {
    window.location.hash = "#/settings/user-settings";
  }

  if (isAuthorRegistryLoading && isRegistryBackedHash(window.location.hash)) {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle="Loading View"
        activePodcastPersonSlug={null}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <section className="dashboard-page">
          <article className="panel panel-accent dashboard-workspace">
            <DashboardLoadingState />
          </article>
        </section>
      </AppShell>
    );
  }

  if (route.kind === "home") {
    return (
      <AppShell
        mode="home"
        activePodcastPersonSlug={null}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <HomePage health={health} error={error} isLoading={isLoading} />
      </AppShell>
    );
  }

  if (route.kind === "overview") {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={getOverviewTitle(route.overview)}
        activePodcastPersonSlug={null}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={route.overview.slug}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <AuthorOverviewPage
          key={route.overview.slug}
          overview={route.overview}
          showWatermark={showWatermark}
        />
      </AppShell>
    );
  }

  if (route.kind === "podcast-person") {
    const personLabel =
      route.personSlug === "michael-saylor" ? "Michael Saylor" : route.personSlug;
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={`User Podcasts: ${personLabel}`}
        activeUserPodcastView={null}
        activePodcastPersonSlug={route.personSlug}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <PodcastPersonPage key={route.personSlug} personSlug={route.personSlug} />
      </AppShell>
    );
  }

  if (route.kind === "user-narrative-mix") {
    const personLabel =
      route.personSlug === "michael-saylor" ? "Michael Saylor" : route.personSlug;
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={`User Narrative Mix: ${personLabel}`}
        activeUserPodcastView="narrative-mix"
        activePodcastPersonSlug={route.personSlug}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <UserNarrativeMixPage personSlug={route.personSlug} />
      </AppShell>
    );
  }

  if (route.kind === "user-narrative-intensity") {
    const personLabel =
      route.personSlug === "michael-saylor" ? "Michael Saylor" : route.personSlug;
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={`User Narrative Intensity: ${personLabel}`}
        activeUserPodcastView="narrative-intensity"
        activePodcastPersonSlug={route.personSlug}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <UserNarrativeIntensityPage personSlug={route.personSlug} />
      </AppShell>
    );
  }

  if (route.kind === "user-beliefs") {
    const personLabel =
      route.personSlug === "michael-saylor" ? "Michael Saylor" : route.personSlug;
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={`User Beliefs: ${personLabel}`}
        activeUserPodcastView="beliefs"
        activePodcastPersonSlug={route.personSlug}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <UserBeliefsPage personSlug={route.personSlug} />
      </AppShell>
    );
  }

  if (route.kind === "mood") {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={getMoodTitle(route.mood)}
        activePodcastPersonSlug={null}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={route.mood.slug}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <AuthorMoodPage key={route.mood.slug} mood={route.mood} showWatermark={showWatermark} />
      </AppShell>
    );
  }

  if (route.kind === "aggregate-mood") {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={getAggregateMoodTitle(route.aggregateMood)}
        activePodcastPersonSlug={null}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={route.aggregateMood.slug}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <AggregateMoodPage
          key={route.aggregateMood.slug}
          aggregateMood={route.aggregateMood}
          showWatermark={showWatermark}
        />
      </AppShell>
    );
  }

  if (route.kind === "heatmap") {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={getHeatmapTitle(route.heatmap)}
        activePodcastPersonSlug={null}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={route.heatmap.slug}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <AuthorHeatmapPage
          key={route.heatmap.slug}
          heatmap={route.heatmap}
          showWatermark={showWatermark}
        />
      </AppShell>
    );
  }

  if (route.kind === "aggregate-narratives") {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle="Aggregate Narratives"
        activePodcastPersonSlug={null}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={true}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateMoodOutliers={navigateMoodOutliers}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <AggregateNarrativesPage showWatermark={showWatermark} />
      </AppShell>
    );
  }

  if (route.kind === "mood-outliers") {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle="Mood Outliers"
        activePodcastPersonSlug={null}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodOutliers
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateMoodOutliers={navigateMoodOutliers}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <MoodOutliersPage apiBasePath="/api/views/aggregate-moods" />
      </AppShell>
    );
  }

  if (route.kind === "price-mentions") {
    const titleMap = {
      heatmap: "Price Mentions — Heatmap",
      distribution: "Price Mentions — Distribution",
      zscore: "Price Mentions — Z-Score",
    };
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={titleMap[route.view]}
        activePodcastPersonSlug={null}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        activePriceMentionsView={route.view}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        {route.view === "heatmap" ? (
          <PriceMentionsPage />
        ) : route.view === "distribution" ? (
          <PriceMentionDistributionPage />
        ) : (
          <PriceMentionZScorePage />
        )}
      </AppShell>
    );
  }

  if (route.kind === "bitcoin-mentions") {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={getBitcoinMentionsTitle(route.bitcoinMentions)}
        activePodcastPersonSlug={null}
        activeBitcoinMentionsSlug={route.bitcoinMentions.slug}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        <BitcoinMentionsPage
          key={route.bitcoinMentions.slug}
          bitcoinMentions={route.bitcoinMentions}
          showWatermark={showWatermark}
        />
      </AppShell>
    );
  }

  if (route.kind === "settings") {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={route.section === "global" ? "Global Settings" : "User Settings"}
        activePodcastPersonSlug={null}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeAggregateNarratives={false}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={route.section}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigatePodcastPerson={navigatePodcastPerson}
        onNavigateAggregateMood={navigateAggregateMood}
        onNavigateAggregateNarratives={navigateAggregateNarratives}
        onNavigateBitcoinMentions={navigateBitcoinMentions}
        onNavigateMood={navigateMood}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        onNavigateGlobalSettings={navigateGlobalSettings}
        onNavigateUserSettings={navigateUserSettings}
        overviews={sortedOverviewDefinitions}
        heatmaps={sortedHeatmapDefinitions}
      >
        {route.section === "global" ? (
          <SettingsPage
            theme={theme}
            onThemeChange={setTheme}
            showWatermark={showWatermark}
            onShowWatermarkChange={setShowWatermark}
            anonymizeUsers={anonymizeUsers}
            onAnonymizeUsersChange={setAnonymizeUsers}
          />
        ) : (
          <UserSettingsPage />
        )}
      </AppShell>
    );
  }

  return (
    <AppShell
      mode="dashboard"
      dashboardTitle="Overview Not Found"
      activePodcastPersonSlug={null}
      activeBitcoinMentionsSlug={null}
      activeAggregateMoodSlug={null}
      activeAggregateNarratives={false}
      activeMoodSlug={null}
      activeOverviewSlug={null}
      activeHeatmapSlug={null}
      activeSettingsSection={null}
      aggregateMoods={aggregateMoodDefinitions}
      bitcoinMentions={sortedBitcoinMentionsDefinitions}
      moods={sortedMoodDefinitions}
      onNavigateHome={navigateHome}
      onNavigatePodcastPerson={navigatePodcastPerson}
      onNavigateAggregateMood={navigateAggregateMood}
      onNavigateAggregateNarratives={navigateAggregateNarratives}
      onNavigateBitcoinMentions={navigateBitcoinMentions}
      onNavigateMood={navigateMood}
      onNavigateOverview={navigateOverview}
      onNavigateHeatmap={navigateHeatmap}
      onNavigateGlobalSettings={navigateGlobalSettings}
      onNavigateUserSettings={navigateUserSettings}
      overviews={sortedOverviewDefinitions}
      heatmaps={sortedHeatmapDefinitions}
    >
      <NotFoundPage />
    </AppShell>
  );
}
