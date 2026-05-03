import { Pin } from "lucide-react";

import type {
  PriceMentionCohortKey,
  PriceMentionCohortOption,
} from "../lib/priceMentionCohorts";

type PriceMentionCohortSidebarProps = {
  cohortOptions: PriceMentionCohortOption[];
  selectedCohortKey: PriceMentionCohortKey;
  pinnedCohortKey: PriceMentionCohortKey | null;
  onSelectedCohortKeyChange: (nextKey: PriceMentionCohortKey) => void;
  onPinnedCohortKeyToggle: (nextKey: PriceMentionCohortKey) => void;
};

export function PriceMentionCohortSidebar({
  cohortOptions,
  selectedCohortKey,
  pinnedCohortKey,
  onSelectedCohortKeyChange,
  onPinnedCohortKeyToggle,
}: PriceMentionCohortSidebarProps) {
  return (
    <aside className="chart-sidebar chart-sidebar-cohorts-only pm-cohort-sidebar">
      <div className="chart-control-card">
        <p className="chart-control-eyebrow">User Cohorts</p>
        <div className="chart-cohort-list" role="group" aria-label="User cohorts">
          {cohortOptions.map((cohortOption) => {
            const isSelected = selectedCohortKey === cohortOption.key;
            const isPinned = pinnedCohortKey === cohortOption.key;

            return (
              <div className="chart-cohort-row" key={cohortOption.key}>
                <button
                  className={`chart-toggle-button chart-cohort-select-button${isSelected ? " is-active" : ""}`}
                  onClick={() => onSelectedCohortKeyChange(cohortOption.key)}
                  type="button"
                >
                  {cohortOption.tagName}
                </button>
                <button
                  aria-label={`${isPinned ? "Unpin" : "Pin"} ${cohortOption.tagName}`}
                  aria-pressed={isPinned}
                  className={`chart-toggle-button chart-pin-button${isPinned ? " is-active" : ""}`}
                  onClick={() => onPinnedCohortKeyToggle(cohortOption.key)}
                  title={isPinned ? "Unpin cohort" : "Pin cohort"}
                  type="button"
                >
                  <Pin aria-hidden="true" className="chart-pin-icon" size={16} strokeWidth={1.9} />
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
