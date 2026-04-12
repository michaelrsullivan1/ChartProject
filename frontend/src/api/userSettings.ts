export type UserSettingsCohortTag = {
  id: number;
  slug: string;
  name: string;
  assigned_user_count: number;
  eligible_user_count: number;
};

export type UserSettingsCohortTagResponse = {
  view: string;
  model: {
    model_key: string;
  };
  eligible_user_count: number;
  cohort_tags: UserSettingsCohortTag[];
};

export type UserSettingsUser = {
  id: number;
  platform_user_id: string;
  username: string;
  display_name: string | null;
  cohort_tags: Array<{
    id: number;
    slug: string;
    name: string;
  }>;
};

export type UserSettingsUsersResponse = {
  view: string;
  model: {
    model_key: string;
  };
  users: UserSettingsUser[];
};

export async function fetchUserSettingsCohortTags(
  options?: {
    eligibleOnly?: boolean;
    signal?: AbortSignal;
  },
): Promise<UserSettingsCohortTagResponse> {
  const query = new URLSearchParams();
  if (options?.eligibleOnly) {
    query.set("eligible_only", "true");
  }

  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  const response = await fetch(`/api/user-settings/cohort-tags${suffix}`, {
    signal: options?.signal,
  });
  if (!response.ok) {
    throw new Error(`User settings cohort tags request failed with status ${response.status}`);
  }

  return (await response.json()) as UserSettingsCohortTagResponse;
}

export async function createUserSettingsCohortTag(name: string): Promise<UserSettingsCohortTag> {
  const response = await fetch("/api/user-settings/cohort-tags", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    throw new Error(`Create cohort tag request failed with status ${response.status}`);
  }

  const payload = (await response.json()) as {
    cohort_tag: UserSettingsCohortTag;
  };
  return payload.cohort_tag;
}

export async function fetchUserSettingsUsers(signal?: AbortSignal): Promise<UserSettingsUsersResponse> {
  const response = await fetch("/api/user-settings/users", { signal });
  if (!response.ok) {
    throw new Error(`User settings users request failed with status ${response.status}`);
  }

  return (await response.json()) as UserSettingsUsersResponse;
}

export async function updateUserSettingsUserCohortTags(
  userId: number,
  tagSlugs: string[],
): Promise<UserSettingsUser> {
  const response = await fetch(`/api/user-settings/users/${userId}/cohort-tags`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      tag_slugs: tagSlugs,
    }),
  });
  if (!response.ok) {
    throw new Error(`Update user cohort tags request failed with status ${response.status}`);
  }

  const payload = (await response.json()) as {
    user: UserSettingsUser;
  };
  return payload.user;
}
