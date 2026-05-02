#!/usr/bin/env bash
# Runs price mention extraction for all tracked/published users (or a single user).
# Default mode is incremental (--only-missing-tweets), safe to re-run at any time.
# Use --full to reprocess all tweets, e.g. after an extractor version bump.

set -eo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SINGLE_USERNAME=""
FULL_MODE=false
ANALYSIS_START="2020-08-01T00:00:00Z"

print_usage() {
  cat <<'EOF'
Usage:
  ./scripts/run-price-mentions-extraction.sh [--username <handle>] [--full]

Options:
  --username <handle>   Process only this user (default: all tracked/published users)
  --full                Reprocess all tweets (drops --only-missing-tweets)
                        Use after tuning extractor weights or bumping extractor version.
                        Default: incremental — only tweets with no existing rows are processed.

Examples:
  ./scripts/run-price-mentions-extraction.sh                      # incremental pass, all users
  ./scripts/run-price-mentions-extraction.sh --username saylor    # incremental, single user
  ./scripts/run-price-mentions-extraction.sh --full               # full reprocess, all users
  ./scripts/run-price-mentions-extraction.sh --username saylor --full
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --username)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --username."
        print_usage
        exit 2
      fi
      SINGLE_USERNAME="$2"
      shift 2
      ;;
    --full)
      FULL_MODE=true
      shift 1
      ;;
    -h|--help)
      print_usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      print_usage
      exit 2
      ;;
  esac
done

cd "$ROOT_DIR"

# Write username list to a temp file.
TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT

if [[ -n "$SINGLE_USERNAME" ]]; then
  echo "$SINGLE_USERNAME" > "$TMPFILE"
else
  python3 - <<'PY' > "$TMPFILE"
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "backend"))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.managed_author_view import ManagedAuthorView
from app.models.user import User

session = SessionLocal()
try:
    rows = session.execute(
        select(User.username)
        .join(ManagedAuthorView, ManagedAuthorView.user_id == User.id)
        .where(
            ManagedAuthorView.is_tracked == True,
            ManagedAuthorView.published == True,
        )
        .order_by(User.username.asc())
    ).scalars().all()
    for username in rows:
        print(username)
finally:
    session.close()
PY
fi

TOTAL=$(wc -l < "$TMPFILE" | tr -d ' ')
if [[ "$TOTAL" -eq 0 ]]; then
  echo "No users to process."
  exit 0
fi

echo "Price mentions extraction"
echo "  Users:          ${TOTAL}"
if [[ "$FULL_MODE" = true ]]; then
  echo "  Mode:           full reprocess"
else
  echo "  Mode:           incremental (--only-missing-tweets)"
fi
echo "  Analysis start: ${ANALYSIS_START}"
echo

SUCCEEDED=0
FAILED=0
FAILED_NAMES=""
INDEX=0

while IFS= read -r USERNAME; do
  INDEX=$((INDEX + 1))
  echo "[${INDEX}/${TOTAL}] ${USERNAME}"

  if [[ "$FULL_MODE" = false ]]; then
    INCREMENTAL_FLAG="--only-missing-tweets"
  else
    INCREMENTAL_FLAG=""
  fi

  if python3 backend/scripts/enrich/extract_tweet_price_mentions.py \
      --username "$USERNAME" \
      --analysis-start "$ANALYSIS_START" \
      $INCREMENTAL_FLAG; then
    SUCCEEDED=$((SUCCEEDED + 1))
  else
    FAILED=$((FAILED + 1))
    FAILED_NAMES="${FAILED_NAMES}  - ${USERNAME}"$'\n'
    echo "    FAILED: ${USERNAME}"
  fi
done < "$TMPFILE"

echo
echo "Done. Succeeded: ${SUCCEEDED}  Failed: ${FAILED}"
if [[ -n "$FAILED_NAMES" ]]; then
  echo "Failed users:"
  echo "$FAILED_NAMES"
  exit 1
fi
