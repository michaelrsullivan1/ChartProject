import { useEffect, useState } from "react";

import {
  createUserSettingsCohortTag,
  fetchUserSettingsCohortTags,
  fetchUserSettingsUsers,
  updateUserSettingsUserCohortTags,
  type UserSettingsCohortTag,
  type UserSettingsUser,
} from "../api/userSettings";

export function UserSettingsPage() {
  const [cohortTags, setCohortTags] = useState<UserSettingsCohortTag[]>([]);
  const [users, setUsers] = useState<UserSettingsUser[]>([]);
  const [newTagName, setNewTagName] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingTag, setIsCreatingTag] = useState(false);
  const [updatingUserIds, setUpdatingUserIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadUserSettings() {
      try {
        const [cohortTagResponse, usersResponse] = await Promise.all([
          fetchUserSettingsCohortTags(),
          fetchUserSettingsUsers(),
        ]);
        if (!cancelled) {
          setCohortTags(cohortTagResponse.cohort_tags);
          setUsers(usersResponse.users);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error ? loadError.message : "Unknown user settings fetch failure",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadUserSettings();

    return () => {
      cancelled = true;
    };
  }, []);

  async function reloadCohortTags() {
    const response = await fetchUserSettingsCohortTags();
    setCohortTags(response.cohort_tags);
  }

  async function handleCreateCohortTag() {
    const cleanedName = newTagName.trim();
    if (!cleanedName) {
      return;
    }

    setIsCreatingTag(true);
    try {
      await createUserSettingsCohortTag(cleanedName);
      setNewTagName("");
      await reloadCohortTags();
      setError(null);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Unknown create tag failure");
    } finally {
      setIsCreatingTag(false);
    }
  }

  async function handleToggleUserTag(user: UserSettingsUser, tagSlug: string) {
    setUpdatingUserIds((current) => {
      const next = new Set(current);
      next.add(user.id);
      return next;
    });

    try {
      const hasTag = user.cohort_tags.some((tag) => tag.slug === tagSlug);
      const nextTagSlugs = hasTag
        ? user.cohort_tags.filter((tag) => tag.slug !== tagSlug).map((tag) => tag.slug)
        : [...user.cohort_tags.map((tag) => tag.slug), tagSlug];
      const updatedUser = await updateUserSettingsUserCohortTags(user.id, nextTagSlugs);

      setUsers((current) =>
        current.map((currentUser) => (currentUser.id === user.id ? updatedUser : currentUser)),
      );
      await reloadCohortTags();
      setError(null);
    } catch (updateError) {
      setError(
        updateError instanceof Error ? updateError.message : "Unknown cohort assignment failure",
      );
    } finally {
      setUpdatingUserIds((current) => {
        const next = new Set(current);
        next.delete(user.id);
        return next;
      });
    }
  }

  return (
    <section className="dashboard-page settings-page">
      <div className="content-stack">
        <article className="panel panel-accent settings-hero-card">
          <p className="eyebrow settings-eyebrow">Configuration</p>
          <div className="settings-hero-header">
            <div>
              <h1 className="settings-title">User settings</h1>
              <p className="status-copy settings-subtitle">
                Assign managed cohort tags to users with scored mood data so Aggregate Moods can
                filter to a single cohort at a time.
              </p>
              {error ? <p className="status-copy">{error}</p> : null}
            </div>
            <div className="settings-status-card">
              <span className="settings-status-label">Current phase</span>
              <strong>Active configuration</strong>
              <p>
                {users.length} eligible users, {cohortTags.length} managed cohort tags.
              </p>
            </div>
          </div>
        </article>

        <article className="panel settings-section settings-section-full">
          <div className="settings-section-header">
            <div>
              <p className="chart-control-eyebrow">Managed Tags</p>
              <h2>Cohort tags</h2>
            </div>
          </div>
          <div className="user-settings-tag-create">
            <input
              className="user-settings-tag-input"
              onChange={(event) => setNewTagName(event.target.value)}
              placeholder="Add a new cohort tag"
              type="text"
              value={newTagName}
            />
            <button
              className="user-settings-tag-button"
              disabled={isCreatingTag || !newTagName.trim()}
              onClick={() => {
                void handleCreateCohortTag();
              }}
              type="button"
            >
              {isCreatingTag ? "Creating..." : "Create tag"}
            </button>
          </div>
          <div className="user-settings-tag-list">
            {cohortTags.map((tag) => (
              <article className="user-settings-tag-chip" key={tag.slug}>
                <strong>{tag.name}</strong>
                <p>
                  Assigned: {tag.assigned_user_count} users | Eligible: {tag.eligible_user_count}
                </p>
              </article>
            ))}
            {cohortTags.length === 0 ? (
              <p className="status-copy">No cohort tags created yet.</p>
            ) : null}
          </div>
        </article>

        <article className="panel settings-section settings-section-full">
          <div className="settings-section-header">
            <div>
              <p className="chart-control-eyebrow">Eligible Users</p>
              <h2>User cohort assignments</h2>
            </div>
          </div>
          {isLoading ? (
            <p className="status-copy">Loading user settings...</p>
          ) : (
            <div className="user-settings-user-list">
              {users.map((user) => {
                const isUpdating = updatingUserIds.has(user.id);
                return (
                  <article className="user-settings-user-card" key={user.id}>
                    <header className="user-settings-user-header">
                      <div>
                        <p className="user-settings-user-name">
                          {user.display_name || user.username}
                        </p>
                        <p className="user-settings-user-handle">@{user.username}</p>
                      </div>
                      <div className="user-settings-user-tags">
                        {user.cohort_tags.map((tag) => (
                          <span className="user-settings-user-tag" key={`${user.id}-${tag.slug}`}>
                            {tag.name}
                          </span>
                        ))}
                        {user.cohort_tags.length === 0 ? (
                          <span className="user-settings-user-tag is-muted">No tags assigned</span>
                        ) : null}
                      </div>
                    </header>
                    <div className="user-settings-assignment-grid">
                      {cohortTags.map((tag) => {
                        const isActive = user.cohort_tags.some(
                          (userTag) => userTag.slug === tag.slug,
                        );
                        return (
                          <button
                            className={`user-settings-assignment-button${isActive ? " is-active" : ""}`}
                            disabled={isUpdating}
                            key={`${user.id}-${tag.slug}`}
                            onClick={() => {
                              void handleToggleUserTag(user, tag.slug);
                            }}
                            type="button"
                          >
                            {tag.name}
                          </button>
                        );
                      })}
                    </div>
                    {isUpdating ? <p className="status-copy">Updating cohort assignment...</p> : null}
                  </article>
                );
              })}
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
