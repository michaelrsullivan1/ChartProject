from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class PathConfig:
    root: Path
    data: Path
    raw: Path
    interim: Path
    processed: Path
    manual: Path
    warehouse: Path
    output: Path
    charts: Path
    animations: Path
    cards: Path


@dataclass(frozen=True)
class AppConfig:
    paths: PathConfig
    duckdb_path: Path
    timezone: str
    log_level: str
    default_granularity: str
    x_api_bearer_token: str | None
    coingecko_api_key: str | None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _build_paths(root: Path) -> PathConfig:
    data = root / "data"
    output = root / "output"
    return PathConfig(
        root=root,
        data=data,
        raw=data / "raw",
        interim=data / "interim",
        processed=data / "processed",
        manual=data / "manual",
        warehouse=data / "warehouse",
        output=output,
        charts=output / "charts",
        animations=output / "animations",
        cards=output / "cards",
    )


@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    root = _repo_root()
    load_dotenv(root / ".env", override=False)
    paths = _build_paths(root)
    return AppConfig(
        paths=paths,
        duckdb_path=paths.warehouse / "analytics.duckdb",
        timezone=os.getenv("PROJECT_TIMEZONE", "UTC"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        default_granularity=os.getenv("DEFAULT_GRANULARITY", "monthly"),
        x_api_bearer_token=os.getenv("X_API_BEARER_TOKEN"),
        coingecko_api_key=os.getenv("COINGECKO_API_KEY"),
    )


def ensure_directories(paths: PathConfig) -> None:
    required_dirs = [
        paths.raw,
        paths.raw / "social",
        paths.raw / "market",
        paths.interim,
        paths.processed,
        paths.manual,
        paths.warehouse,
        paths.charts,
        paths.animations,
        paths.cards,
    ]
    for directory in required_dirs:
        directory.mkdir(parents=True, exist_ok=True)
