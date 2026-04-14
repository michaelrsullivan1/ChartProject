import { useEffect, useState } from "react";

import { fetchAuthorRegistry } from "./api/authorRegistry";
import { fetchHealth } from "./api/health";
import { AppShell } from "./components/AppShell";
import {
  aggregateMoodDefinitions,
  findAggregateMoodBySlug,
  getAggregateMoodHash,
  getAggregateMoodTitle,
  type AggregateMoodDefinition,
} from "./config/aggregateMoods";
import {
  bitcoinMentionsDefinitions as defaultBitcoinMentionsDefinitions,
  getBitcoinMentionsLabel,
  getBitcoinMentionsHash,
  getBitcoinMentionsTitle,
  type BitcoinMentionsDefinition,
} from "./config/bitcoinMentions";
import {
  getHeatmapHash,
  getHeatmapLabel,
  getHeatmapTitle,
  heatmapDefinitions as defaultHeatmapDefinitions,
  type HeatmapDefinition,
} from "./config/heatmaps";
import {
  getMoodLabel,
  getMoodHash,
  getMoodTitle,
  moodDefinitions as defaultMoodDefinitions,
  type MoodDefinition,
} from "./config/moods";
import {
  getOverviewLabel,
  getOverviewHash,
  getOverviewTitle,
  overviewDefinitions as defaultOverviewDefinitions,
  type OverviewDefinition,
} from "./config/overviews";
import { HomePage } from "./pages/HomePage";
import { AuthorHeatmapPage } from "./pages/AuthorHeatmapPage";
import { AuthorMoodPage } from "./pages/AuthorMoodPage";
import { AggregateMoodPage } from "./pages/AggregateMoodPage";
import { BitcoinMentionsPage } from "./pages/BitcoinMentionsPage";
import { AuthorOverviewPage } from "./pages/MichaelSaylorVsBtcPage";
import { NotFoundPage } from "./pages/NotFoundPage";
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
  | { kind: "aggregate-mood"; aggregateMood: AggregateMoodDefinition }
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

function getRouteFromHash(hash: string, definitions: RouteDefinitions): AppRoute {
  if (hash === "" || hash === "#" || hash === "#/") {
    return { kind: "home" };
  }

  if (hash === "#/bitcoin-mentions") {
    const bitcoinMentions = definitions.bitcoinMentions[0];
    return bitcoinMentions ? { kind: "bitcoin-mentions", bitcoinMentions } : { kind: "not-found" };
  }

  if (hash === "#/aggregate-moods") {
    const aggregateMood = aggregateMoodDefinitions[0];
    return aggregateMood ? { kind: "aggregate-mood", aggregateMood } : { kind: "not-found" };
  }

  if (hash.startsWith("#/bitcoin-mentions/")) {
    const slug = decodeURIComponent(hash.slice("#/bitcoin-mentions/".length));
    const bitcoinMentions = findBySlug(definitions.bitcoinMentions, slug);
    return bitcoinMentions ? { kind: "bitcoin-mentions", bitcoinMentions } : { kind: "not-found" };
  }

  if (hash.startsWith("#/aggregate-moods/")) {
    const slug = decodeURIComponent(hash.slice("#/aggregate-moods/".length));
    const aggregateMood = findAggregateMoodBySlug(slug);
    return aggregateMood ? { kind: "aggregate-mood", aggregateMood } : { kind: "not-found" };
  }

  if (hash.startsWith("#/overviews/")) {
    const slug = decodeURIComponent(hash.slice("#/overviews/".length));
    const overview = findBySlug(definitions.overviews, slug);
    return overview ? { kind: "overview", overview } : { kind: "not-found" };
  }

  if (hash.startsWith("#/moods/")) {
    const slug = decodeURIComponent(hash.slice("#/moods/".length));
    const mood = findBySlug(definitions.moods, slug);
    return mood ? { kind: "mood", mood } : { kind: "not-found" };
  }

  if (hash === "#/narratives" || hash === "#/heatmaps") {
    const heatmap = definitions.heatmaps[0];
    return heatmap ? { kind: "heatmap", heatmap } : { kind: "not-found" };
  }

  if (hash.startsWith("#/narratives/")) {
    const slug = decodeURIComponent(hash.slice("#/narratives/".length));
    const heatmap = findBySlug(definitions.heatmaps, slug);
    return heatmap ? { kind: "heatmap", heatmap } : { kind: "not-found" };
  }

  if (hash.startsWith("#/heatmaps/")) {
    const slug = decodeURIComponent(hash.slice("#/heatmaps/".length));
    const heatmap = findBySlug(definitions.heatmaps, slug);
    return heatmap ? { kind: "heatmap", heatmap } : { kind: "not-found" };
  }

  if (hash === "#/settings") {
    return { kind: "settings", section: "global" };
  }

  if (hash === "#/settings/global-settings") {
    return { kind: "settings", section: "global" };
  }

  if (hash === "#/settings/user-settings") {
    return { kind: "settings", section: "user" };
  }

  return { kind: "not-found" };
}

function mergeDefinitions<T extends { slug: string }>(base: T[], incoming: T[]): T[] {
  const next = [...base];
  const indexBySlug = new Map<string, number>();
  for (const [index, item] of next.entries()) {
    indexBySlug.set(item.slug, index);
  }

  for (const item of incoming) {
    const existingIndex = indexBySlug.get(item.slug);
    if (existingIndex === undefined) {
      indexBySlug.set(item.slug, next.length);
      next.push(item);
      continue;
    }
    next[existingIndex] = item;
  }

  return next;
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
  const [bitcoinMentionsDefinitions, setBitcoinMentionsDefinitions] = useState<BitcoinMentionsDefinition[]>(
    defaultBitcoinMentionsDefinitions,
  );
  const [moodDefinitions, setMoodDefinitions] = useState<MoodDefinition[]>(defaultMoodDefinitions);
  const [overviewDefinitions, setOverviewDefinitions] = useState<OverviewDefinition[]>(
    defaultOverviewDefinitions,
  );
  const [heatmapDefinitions, setHeatmapDefinitions] = useState<HeatmapDefinition[]>(
    defaultHeatmapDefinitions,
  );
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [route, setRoute] = useState<AppRoute>(() =>
    getRouteFromHash(window.location.hash, {
      bitcoinMentions: sortDefinitionsByLabel(
        defaultBitcoinMentionsDefinitions,
        getBitcoinMentionsLabel,
      ),
      moods: sortDefinitionsByLabel(defaultMoodDefinitions, getMoodLabel),
      overviews: sortDefinitionsByLabel(defaultOverviewDefinitions, getOverviewLabel),
      heatmaps: sortDefinitionsByLabel(defaultHeatmapDefinitions, getHeatmapLabel),
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
        setOverviewDefinitions((current) =>
          mergeDefinitions(
            current,
            registry.overviews.map((item) => ({
              slug: item.slug,
              username: item.username,
              apiBasePath: item.api_base_path,
            })),
          ),
        );
        setMoodDefinitions((current) =>
          mergeDefinitions(
            current,
            registry.moods.map((item) => ({
              slug: item.slug,
              username: item.username,
              apiBasePath: item.api_base_path,
            })),
          ),
        );
        setHeatmapDefinitions((current) =>
          mergeDefinitions(
            current,
            registry.heatmaps.map((item) => ({
              slug: item.slug,
              username: item.username,
              apiBasePath: item.api_base_path,
            })),
          ),
        );
        setBitcoinMentionsDefinitions((current) =>
          mergeDefinitions(
            current,
            registry.bitcoin_mentions.map((item) => ({
              slug: item.slug,
              username: item.username,
            })),
          ),
        );
      } catch (loadError) {
        console.warn("ChartProject author registry request failed; continuing with static config", loadError);
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

  function navigateAggregateMood(slug: string) {
    window.location.hash = getAggregateMoodHash(slug);
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

  if (route.kind === "home") {
    return (
      <AppShell
        mode="home"
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigateAggregateMood={navigateAggregateMood}
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
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeMoodSlug={null}
        activeOverviewSlug={route.overview.slug}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigateAggregateMood={navigateAggregateMood}
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

  if (route.kind === "mood") {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={getMoodTitle(route.mood)}
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeMoodSlug={route.mood.slug}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigateAggregateMood={navigateAggregateMood}
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
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={route.aggregateMood.slug}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigateAggregateMood={navigateAggregateMood}
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
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={route.heatmap.slug}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigateAggregateMood={navigateAggregateMood}
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

  if (route.kind === "bitcoin-mentions") {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={getBitcoinMentionsTitle(route.bitcoinMentions)}
        activeBitcoinMentionsSlug={route.bitcoinMentions.slug}
        activeAggregateMoodSlug={null}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={null}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigateAggregateMood={navigateAggregateMood}
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
        activeBitcoinMentionsSlug={null}
        activeAggregateMoodSlug={null}
        activeMoodSlug={null}
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        activeSettingsSection={route.section}
        aggregateMoods={aggregateMoodDefinitions}
        bitcoinMentions={sortedBitcoinMentionsDefinitions}
        moods={sortedMoodDefinitions}
        onNavigateHome={navigateHome}
        onNavigateAggregateMood={navigateAggregateMood}
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
      activeBitcoinMentionsSlug={null}
      activeAggregateMoodSlug={null}
      activeMoodSlug={null}
      activeOverviewSlug={null}
      activeHeatmapSlug={null}
      activeSettingsSection={null}
      aggregateMoods={aggregateMoodDefinitions}
      bitcoinMentions={sortedBitcoinMentionsDefinitions}
      moods={sortedMoodDefinitions}
      onNavigateHome={navigateHome}
      onNavigateAggregateMood={navigateAggregateMood}
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
