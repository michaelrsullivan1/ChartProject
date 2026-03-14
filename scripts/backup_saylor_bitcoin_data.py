#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTERNAL_BACKUP_ROOT = PROJECT_ROOT / "data" / "backups"
DEFAULT_EXTERNAL_BACKUP_ROOT = Path.home() / "Backups" / "ChartProjectData"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create redundant backups for Saylor Bitcoin snapshot + raw ingest artifacts"
    )
    parser.add_argument(
        "--internal-root",
        default=str(DEFAULT_INTERNAL_BACKUP_ROOT),
        help="Primary backup root (inside project)",
    )
    parser.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_BACKUP_ROOT),
        help="Secondary backup root (outside project)",
    )
    parser.add_argument(
        "--no-external",
        action="store_true",
        help="Skip external backup copy",
    )
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_file(src: Path, dst: Path) -> dict:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    stat = dst.stat()
    return {
        "path": str(dst),
        "size_bytes": stat.st_size,
        "sha256": _sha256(dst),
    }


def _expand_sources() -> list[Path]:
    candidates = [
        PROJECT_ROOT / "data" / "warehouse" / "analytics.duckdb",
        PROJECT_ROOT / "data" / "processed" / "social" / "saylor_bitcoin_posts_canonical.parquet",
        PROJECT_ROOT / "data" / "processed" / "social" / "saylor_bitcoin_posts_canonical.csv",
        PROJECT_ROOT / "data" / "processed" / "social" / "saylor_bitcoin_posts_snapshot_metadata.json",
        PROJECT_ROOT / "data" / "interim" / "social" / "saylor_bitcoin_history_checkpoint.json",
        PROJECT_ROOT / "data" / "interim" / "social" / "saylor_bitcoin_history_pre2020_checkpoint.json",
    ]

    # Keep all raw/processed versioned artifacts tied to this dataset.
    candidates.extend((PROJECT_ROOT / "data" / "processed" / "social").glob("saylor_bitcoin*.parquet"))
    candidates.extend((PROJECT_ROOT / "data" / "raw" / "social").glob("saylor_bitcoin*.json"))
    candidates.extend((PROJECT_ROOT / "data" / "interim" / "social").glob("*bitcoin*.json"))

    seen: set[Path] = set()
    existing: list[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen or not resolved.exists() or not resolved.is_file():
            continue
        seen.add(resolved)
        existing.append(resolved)
    return sorted(existing)


def backup_to_root(root: Path, stamp: str, sources: list[Path]) -> tuple[Path, list[dict]]:
    backup_dir = root / f"saylor_bitcoin_backup_{stamp}"
    manifests: list[dict] = []

    for src in sources:
        rel = src.relative_to(PROJECT_ROOT)
        dst = backup_dir / rel
        copied = _copy_file(src, dst)
        manifests.append(
            {
                "source": str(src),
                "relative_path": str(rel),
                **copied,
            }
        )

    manifest_path = backup_dir / "backup_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "project_root": str(PROJECT_ROOT),
                "backup_root": str(root),
                "backup_dir": str(backup_dir),
                "file_count": len(manifests),
                "files": manifests,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    latest_pointer = root / "LATEST_BACKUP.txt"
    latest_pointer.parent.mkdir(parents=True, exist_ok=True)
    latest_pointer.write_text(str(backup_dir), encoding="utf-8")

    return backup_dir, manifests


def main() -> None:
    args = parse_args()

    sources = _expand_sources()
    if not sources:
        raise SystemExit("No source files found to back up")

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    internal_root = Path(args.internal_root).resolve()
    internal_dir, internal_files = backup_to_root(internal_root, stamp, sources)

    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "policy": {
            "counting_mode": "include_original_reposts_quotes",
            "source_filter": "from:saylor (bitcoin OR btc OR #bitcoin OR #btc)",
        },
        "source_file_count": len(sources),
        "internal_backup": {
            "path": str(internal_dir),
            "file_count": len(internal_files),
        },
    }

    if not args.no_external:
        external_root = Path(args.external_root).resolve()
        external_dir, external_files = backup_to_root(external_root, stamp, sources)
        output["external_backup"] = {
            "path": str(external_dir),
            "file_count": len(external_files),
        }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
