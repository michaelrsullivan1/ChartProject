import { useEffect, useState } from "react";

import { fetchHealth } from "./api/health";
import { AppShell } from "./components/AppShell";
import {
  findHeatmapBySlug,
  getHeatmapHash,
  getHeatmapTitle,
  heatmapDefinitions,
  type HeatmapDefinition,
} from "./config/heatmaps";
import {
  findOverviewBySlug,
  getOverviewHash,
  getOverviewTitle,
  overviewDefinitions,
  type OverviewDefinition,
} from "./config/overviews";
import { HomePage } from "./pages/HomePage";
import { AuthorHeatmapPage } from "./pages/AuthorHeatmapPage";
import { AuthorOverviewPage } from "./pages/MichaelSaylorVsBtcPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import type { HealthResponse } from "./types/health";

type AppRoute =
  | { kind: "home" }
  | { kind: "overview"; overview: OverviewDefinition }
  | { kind: "heatmap"; heatmap: HeatmapDefinition }
  | { kind: "not-found" };

function getRouteFromHash(hash: string): AppRoute {
  if (hash === "" || hash === "#" || hash === "#/") {
    return { kind: "home" };
  }

  if (hash.startsWith("#/overviews/")) {
    const slug = decodeURIComponent(hash.slice("#/overviews/".length));
    const overview = findOverviewBySlug(slug);
    return overview ? { kind: "overview", overview } : { kind: "not-found" };
  }

  if (hash.startsWith("#/heatmaps/")) {
    const slug = decodeURIComponent(hash.slice("#/heatmaps/".length));
    const heatmap = findHeatmapBySlug(slug);
    return heatmap ? { kind: "heatmap", heatmap } : { kind: "not-found" };
  }

  return { kind: "not-found" };
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [route, setRoute] = useState<AppRoute>(() => getRouteFromHash(window.location.hash));

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
    function handleHashChange() {
      setRoute(getRouteFromHash(window.location.hash));
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, []);

  function navigateHome() {
    window.location.hash = "#/";
  }

  function navigateOverview(slug: string) {
    window.location.hash = getOverviewHash(slug);
  }

  function navigateHeatmap(slug: string) {
    window.location.hash = getHeatmapHash(slug);
  }

  if (route.kind === "home") {
    return (
      <AppShell
        mode="home"
        activeOverviewSlug={null}
        activeHeatmapSlug={null}
        onNavigateHome={navigateHome}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        overviews={overviewDefinitions}
        heatmaps={heatmapDefinitions}
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
        activeOverviewSlug={route.overview.slug}
        activeHeatmapSlug={null}
        onNavigateHome={navigateHome}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        overviews={overviewDefinitions}
        heatmaps={heatmapDefinitions}
      >
        <AuthorOverviewPage overview={route.overview} />
      </AppShell>
    );
  }

  if (route.kind === "heatmap") {
    return (
      <AppShell
        mode="dashboard"
        dashboardTitle={getHeatmapTitle(route.heatmap)}
        activeOverviewSlug={null}
        activeHeatmapSlug={route.heatmap.slug}
        onNavigateHome={navigateHome}
        onNavigateOverview={navigateOverview}
        onNavigateHeatmap={navigateHeatmap}
        overviews={overviewDefinitions}
        heatmaps={heatmapDefinitions}
      >
        <AuthorHeatmapPage heatmap={route.heatmap} />
      </AppShell>
    );
  }

  return (
    <AppShell
      mode="dashboard"
      dashboardTitle="Overview Not Found"
      activeOverviewSlug={null}
      activeHeatmapSlug={null}
      onNavigateHome={navigateHome}
      onNavigateOverview={navigateOverview}
      onNavigateHeatmap={navigateHeatmap}
      overviews={overviewDefinitions}
      heatmaps={heatmapDefinitions}
    >
      <NotFoundPage />
    </AppShell>
  );
}
