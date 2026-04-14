from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.author_registry import audit_tracked_authors


def main() -> None:
    payload = audit_tracked_authors()
    pprint(payload)
    if not payload["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
