"""Tests for zksato-core config module."""

import pytest
import tempfile
import tomllib
from pathlib import Path

from zksato_core.config import (
    BaseConfig,
    DatabaseConfig,
    RedisConfig,
    LoggingConfig,
    AuthConfig,
    load_toml_config,
    merge_configs,
)


def test_base_config_defaults():
    class TestConfig(BaseConfig):
        name: str = "test"
        value: int = 42

    config = TestConfig()
    assert config.name == "test"
    assert config.value == 42


def test_database_config():
    config = DatabaseConfig()
    assert config.url == "sqlite+aiosqlite:///./zksato.db"
    assert config.pool_size == 5
    assert config.max_overflow == 10
    assert config.echo is False


def test_redis_config():
    config = RedisConfig()
    assert config.url == "redis://localhost:6379/0"
    assert config.max_connections == 10


def test_logging_config():
    config = LoggingConfig()
    assert config.level == "INFO"
    assert config.json is True
    assert config.otel_service_name == "zksato"


def test_auth_config():
    config = AuthConfig()
    assert config.required is False
    assert config.api_keys == ""
    assert config.session_cookie_name == "zksato_session"
    assert config.session_ttl_seconds == 1800
    assert config.csrf_required is True


def test_load_toml_config():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('key = "value"\nnumber = 42\n')
        f.flush()
        path = Path(f.name)

    try:
        config = load_toml_config(path)
        assert config == {"key": "value", "number": 42}
    finally:
        path.unlink()


def test_load_toml_config_missing():
    config = load_toml_config(Path("/nonexistent/path.toml"))
    assert config == {}


def test_merge_configs():
    base = {"a": 1, "b": {"x": 10, "y": 20}}
    override = {"b": {"x": 100}, "c": 3}
    result = merge_configs(base, override)
    assert result == {"a": 1, "b": {"x": 100, "y": 20}, "c": 3}


def test_merge_configs_no_override():
    base = {"a": 1, "b": 2}
    override = {}
    result = merge_configs(base, override)
    assert result == {"a": 1, "b": 2}


def test_merge_configs_new_keys():
    base = {"a": 1}
    override = {"b": 2, "c": 3}
    result = merge_configs(base, override)
    assert result == {"a": 1, "b": 2, "c": 3}