import { useEffect, useState } from "react";

import { MichaelSaylorVsBtcPage } from "./pages/MichaelSaylorVsBtcPage";
import { fetchHealth } from "./api/health";
import { AppShell } from "./components/AppShell";
import { HomePage } from "./pages/HomePage";
import type { HealthResponse } from "./types/health";

type PageKey = "home" | "michael-saylor-vs-btc";

function getPageFromHash(hash: string): PageKey {
  return hash === "#/michael-saylor-vs-btc" ? "michael-saylor-vs-btc" : "home";
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activePage, setActivePage] = useState<PageKey>(() => getPageFromHash(window.location.hash));

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
      setActivePage(getPageFromHash(window.location.hash));
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, []);

  function navigate(page: PageKey) {
    const nextHash = page === "michael-saylor-vs-btc" ? "#/michael-saylor-vs-btc" : "#/";
    window.location.hash = nextHash;
  }

  return (
    <AppShell activePage={activePage} onNavigate={navigate}>
      {activePage === "michael-saylor-vs-btc" ? (
        <MichaelSaylorVsBtcPage />
      ) : (
        <HomePage health={health} error={error} isLoading={isLoading} />
      )}
    </AppShell>
  );
}
