import { useEffect, useState } from "react";

import { fetchHealth } from "./api/health";
import { AppShell } from "./components/AppShell";
import { HomePage } from "./pages/HomePage";
import type { HealthResponse } from "./types/health";

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadHealth() {
      try {
        const response = await fetchHealth();
        if (!cancelled) {
          setHealth(response);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error ? loadError.message : "Unknown health check failure",
          );
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
      <HomePage health={health} error={error} />
    </AppShell>
  );
}
