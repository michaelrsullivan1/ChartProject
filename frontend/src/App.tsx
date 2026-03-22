import { useEffect, useState } from "react";

import { fetchHealth } from "./api/health";
import { AppShell } from "./components/AppShell";
import { HomePage } from "./pages/HomePage";
import type { HealthResponse } from "./types/health";

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

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

  return (
    <AppShell>
      <HomePage health={health} error={error} isLoading={isLoading} />
    </AppShell>
  );
}
