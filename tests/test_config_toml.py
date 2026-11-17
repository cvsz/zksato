"""TOML settings overlay: path resolution, precedence, and fail-closed safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from zksato.config import DEFAULT_TOML_PATH, Settings

REPO_SETTINGS = Path(__file__).resolve().parents[1] / "config" / "settings.toml"


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "settings.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_default_path_is_repo_config_file() -> None:
    assert DEFAULT_TOML_PATH == REPO_SETTINGS
    assert DEFAULT_TOML_PATH.exists()


def test_config_file_env_var_overrides_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, "[risk]\nmax_positions = 3\n")
    monkeypatch.setenv("ZKSATO_CONFIG_FILE", str(path))
    assert Settings._apply_toml_overrides(Settings()).max_positions == 3


def test_repo_settings_apply_without_loosening_risk() -> None:
    base = Settings()
    applied = Settings._apply_toml_overrides(base, REPO_SETTINGS)
    # [research] max_drawdown_pct = 20 must not leak into the risk limit.
    assert applied.max_drawdown_pct == base.max_drawdown_pct == 5.0
    assert applied.trading_mode == "paper"
    assert applied.tradingview_webhook_secret is None
    # Deployment secret-file paths come from env, so local runs stay offline.
    assert applied.postgres_password_file is None
    assert applied.redis_password_file is None


def test_section_values_are_applied(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "[risk]\nmax_positions = 3\n[coordination]\nlock_ttl_seconds = 45\n",
    )
    applied = Settings._apply_toml_overrides(Settings(), path)
    assert applied.max_positions == 3
    assert applied.coordination_lock_ttl_seconds == 45


def test_environment_variables_take_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ZKSATO_MAX_POSITIONS", "2")
    path = _write(tmp_path, "[risk]\nmax_positions = 9\n")
    assert Settings._apply_toml_overrides(Settings(), path).max_positions == 2


def test_toml_cannot_enable_live_trading(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        '[application]\ntrading_mode = "live"\n[live]\ntrading_enabled = true\n',
    )
    applied = Settings._apply_toml_overrides(Settings(), path)
    assert applied.trading_mode == "paper"
    assert applied.live_trading_enabled is False


def test_toml_cannot_set_secrets(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        '[tradingview]\nwebhook_secret = "committed"\n[telegram]\nbot_token = "x"\n',
    )
    applied = Settings._apply_toml_overrides(Settings(), path)
    assert applied.tradingview_webhook_secret is None
    assert applied.telegram_bot_token is None


def test_secret_file_paths_are_allowed(tmp_path: Path) -> None:
    path = _write(tmp_path, '[postgres]\npassword_file = "/run/secrets/pg"\n')
    applied = Settings._apply_toml_overrides(Settings(), path)
    assert applied.postgres_password_file == "/run/secrets/pg"


def test_empty_strings_are_treated_as_unset(tmp_path: Path) -> None:
    path = _write(tmp_path, '[database]\nredis_url = ""\n')
    assert Settings._apply_toml_overrides(Settings(), path).redis_url is None


def test_unknown_keys_are_ignored(tmp_path: Path) -> None:
    path = _write(tmp_path, "[research]\nmax_drawdown_pct = 20.0\n[nope]\nx = 1\n")
    assert Settings._apply_toml_overrides(Settings(), path).max_drawdown_pct == 5.0


def test_ambiguous_mapping_fails_closed(tmp_path: Path) -> None:
    path = _write(tmp_path, "[risk]\nmax_positions = 3\n[strategy]\nmax_positions = 4\n")
    with pytest.raises(ValueError, match="max_positions"):
        Settings._apply_toml_overrides(Settings(), path)


def test_invalid_value_fails_closed(tmp_path: Path) -> None:
    path = _write(tmp_path, "[strategy]\npoll_interval_seconds = 1000\n")
    with pytest.raises(ValueError):
        Settings._apply_toml_overrides(Settings(), path)


def test_malformed_file_fails_closed(tmp_path: Path) -> None:
    path = _write(tmp_path, "[risk\nmax_positions = \n")
    with pytest.raises(ValueError):
        Settings._apply_toml_overrides(Settings(), path)


def test_missing_file_leaves_settings_unchanged(tmp_path: Path) -> None:
    base = Settings()
    assert Settings._apply_toml_overrides(base, tmp_path / "absent.toml") is base
