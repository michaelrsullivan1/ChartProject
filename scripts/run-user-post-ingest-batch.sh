#!/usr/bin/env bash

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

USERNAME=""
ANALYSIS_START=""
PASS_ANALYSIS_START=false

print_usage() {
  cat <<'EOF'
Usage:
  ./scripts/run-user-post-ingest-batch.sh --username <handle> [--analysis-start <UTC_ISO8601>]

Runs these steps in order for one user:
  2) normalize_archived_user
  3) validate_normalized_user
  4) score_tweet_sentiment
  5) score_tweet_moods
  6) extract_tweet_keywords
  7) sync_managed_author_view

Notes:
  - This script intentionally does NOT run fetch_user_tweets_history.py.
  - This script intentionally does NOT run rebuild_aggregate_snapshots.py.
  - If --analysis-start is omitted, step 6 auto-uses the user's first normalized tweet timestamp.
  - It stops immediately on the first failure and prints which step failed.
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
      USERNAME="$2"
      shift 2
      ;;
    --analysis-start)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --analysis-start."
        print_usage
        exit 2
      fi
      ANALYSIS_START="$2"
      PASS_ANALYSIS_START=true
      shift 2
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

if [[ -z "$USERNAME" ]]; then
  echo "--username is required."
  print_usage
  exit 2
fi

resolve_first_tweet_analysis_start() {
  BATCH_USERNAME="$USERNAME" python3 - <<'PY'
from datetime import UTC
import os
from pathlib import Path
import sys

from sqlalchemy import func, select

username = os.environ["BATCH_USERNAME"].strip()
if not username:
    raise SystemExit("Username is empty.")

backend_root = Path.cwd() / "backend"
sys.path.insert(0, str(backend_root))

from app.db.session import SessionLocal  # noqa: E402
from app.models.tweet import Tweet  # noqa: E402
from app.models.user import User  # noqa: E402

session = SessionLocal()
try:
    user = session.scalar(select(User).where(func.lower(User.username) == username.lower()))
    if user is None:
        raise SystemExit(f"No canonical user found for username={username!r}.")

    first_tweet_at = session.scalar(
        select(func.min(Tweet.created_at_platform)).where(Tweet.author_user_id == user.id)
    )
    if first_tweet_at is None:
        raise SystemExit(
            f"No canonical tweets found for username={username!r}. "
            "Run normalization first."
        )

    print(first_tweet_at.astimezone(UTC).isoformat().replace("+00:00", "Z"))
finally:
    session.close()
PY
}

run_step() {
  local step_number="$1"
  local step_name="$2"
  shift 2

  echo
  echo "==> Step ${step_number}: ${step_name}"
  echo "    Command: $*"

  if "$@"; then
    echo "    Result: success"
    return 0
  fi

  local exit_code=$?
  echo "    Result: FAILED at step ${step_number} (${step_name})"
  echo "    Exit code: ${exit_code}"
  exit "$exit_code"
}

cd "$ROOT_DIR"

echo "Running post-ingest batch for username=${USERNAME}"

run_step "2" "normalize_archived_user" \
  python3 backend/scripts/normalize/normalize_archived_user.py --username "$USERNAME"

run_step "3" "validate_normalized_user" \
  python3 backend/scripts/validate/validate_normalized_user.py --username "$USERNAME"

run_step "4" "score_tweet_sentiment" \
  python3 backend/scripts/enrich/score_tweet_sentiment.py --username "$USERNAME"

run_step "5" "score_tweet_moods" \
  python3 backend/scripts/enrich/score_tweet_moods.py --username "$USERNAME"

if [[ "$PASS_ANALYSIS_START" == "true" ]]; then
  EFFECTIVE_ANALYSIS_START="$ANALYSIS_START"
  echo "Using provided analysis start for step 6: ${EFFECTIVE_ANALYSIS_START}"
else
  echo "Resolving first normalized tweet timestamp for step 6..."
  if ! EFFECTIVE_ANALYSIS_START="$(resolve_first_tweet_analysis_start)"; then
    echo "Failed to resolve first normalized tweet timestamp for username=${USERNAME}."
    exit 1
  fi
  echo "Using auto-resolved analysis start for step 6: ${EFFECTIVE_ANALYSIS_START}"
fi

run_step "6" "extract_tweet_keywords" \
  python3 backend/scripts/enrich/extract_tweet_keywords.py \
    --username "$USERNAME" \
    --analysis-start "$EFFECTIVE_ANALYSIS_START"

run_step "7" "sync_managed_author_view" \
  python3 backend/scripts/views/sync_managed_author_view.py \
    --username "$USERNAME" \
    --published

echo
echo "Post-ingest batch completed for username=${USERNAME}"
echo "Reminder: run snapshot rebuild separately if needed:"
echo "  cd $ROOT_DIR/backend"
echo "  python3 scripts/cache/rebuild_aggregate_snapshots.py --delete-stale"
