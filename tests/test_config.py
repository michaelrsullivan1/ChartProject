from chartproject.core.config import ensure_directories, load_config


def test_load_config_has_expected_defaults() -> None:
    config = load_config()
    assert config.timezone
    assert config.log_level
    assert config.default_granularity in {"weekly", "monthly", "daily", "hourly"}
    assert config.duckdb_path.name == "analytics.duckdb"


def test_ensure_directories_creates_required_paths() -> None:
    config = load_config()
    ensure_directories(config.paths)
    assert config.paths.raw.exists()
    assert config.paths.warehouse.exists()
    assert config.paths.charts.exists()
