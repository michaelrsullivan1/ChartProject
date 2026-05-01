export type ManagedNarrative = {
  id: number;
  slug: string;
  name: string;
  phrase: string;
};

export type ManagedNarrativesResponse = {
  view: string;
  narratives: ManagedNarrative[];
};

export async function fetchManagedNarratives(signal?: AbortSignal): Promise<ManagedNarrativesResponse> {
  const response = await fetch("/api/global-settings/narratives", { signal });
  if (!response.ok) {
    throw new Error(`Global settings narratives request failed with status ${response.status}`);
  }

  return (await response.json()) as ManagedNarrativesResponse;
}

export async function createManagedNarrative(phrase: string): Promise<ManagedNarrative> {
  const response = await fetch("/api/global-settings/narratives", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ phrase }),
  });
  if (!response.ok) {
    throw new Error(`Create managed narrative request failed with status ${response.status}`);
  }

  const payload = (await response.json()) as {
    narrative: ManagedNarrative;
  };
  return payload.narrative;
}

export async function updateManagedNarrative(
  narrativeId: number,
  phrase: string,
): Promise<ManagedNarrative> {
  const response = await fetch(`/api/global-settings/narratives/${narrativeId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ phrase }),
  });
  if (!response.ok) {
    throw new Error(`Update managed narrative request failed with status ${response.status}`);
  }

  const payload = (await response.json()) as {
    narrative: ManagedNarrative;
  };
  return payload.narrative;
}
