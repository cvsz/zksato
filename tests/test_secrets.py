"""Tests for zksato.secrets — AWSSecretManagerSettingsSource.

Coverage targets:
- Disabled by default when ZKSATO_USE_AWS_SECRETS is absent / false.
- get_field_value falls through to env-var lookup with ZKSATO_ prefix.
- get_field_value returns (None, name, False) when neither cache nor env has the value.
- prepare_field_value is a transparent passthrough.
- __call__ aggregates only fields with a value.
- Cache path is exercised via a monkey-patched secrets_cache.
"""

from __future__ import annotations

import os

import pytest

from zksato.secrets import AWSSecretManagerSettingsSource

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source() -> AWSSecretManagerSettingsSource:
    """Build a source instance with AWS loading disabled."""
    os.environ["ZKSATO_USE_AWS_SECRETS"] = "false"
    try:
        from zksato.config import Settings

        return AWSSecretManagerSettingsSource(Settings)
    finally:
        os.environ.pop("ZKSATO_USE_AWS_SECRETS", None)


# ---------------------------------------------------------------------------
# Enabled flag
# ---------------------------------------------------------------------------


def test_source_disabled_by_default() -> None:
    """AWS Secrets Manager is disabled unless ZKSATO_USE_AWS_SECRETS is truthy."""
    src = _make_source()
    assert src.enabled is False
    assert src.secrets_cache == {}


@pytest.mark.parametrize("flag", ["true", "1", "yes"])
def test_source_enabled_by_truthy_env(flag: str) -> None:
    """Truthy values for ZKSATO_USE_AWS_SECRETS flip the enabled flag.

    The actual boto3 call is expected to fail (no real AWS), but the flag
    itself must be set correctly before any network call is attempted.
    """
    os.environ["ZKSATO_USE_AWS_SECRETS"] = flag
    try:
        from zksato.config import Settings

        # _load_secrets will silently log and return when boto3 is absent or
        # the endpoint is unreachable — we only assert the flag, not the cache.
        src = AWSSecretManagerSettingsSource(Settings)
        assert src.enabled is True
    finally:
        os.environ.pop("ZKSATO_USE_AWS_SECRETS", None)


# ---------------------------------------------------------------------------
# get_field_value — env-var path
# ---------------------------------------------------------------------------


def test_get_field_value_reads_env_var_with_prefix() -> None:
    """get_field_value returns (value, name, False) when ZKSATO_<FIELD> is set."""
    from pydantic.fields import FieldInfo

    src = _make_source()
    os.environ["ZKSATO_TRADING_MODE"] = "paper"
    try:
        value, key, is_complex = src.get_field_value(FieldInfo(), "trading_mode")
        assert value == "paper"
        assert key == "trading_mode"
        assert is_complex is False
    finally:
        os.environ.pop("ZKSATO_TRADING_MODE", None)


def test_get_field_value_returns_none_when_absent() -> None:
    """get_field_value returns (None, name, False) when nothing is configured."""
    from pydantic.fields import FieldInfo

    src = _make_source()
    env_key = "ZKSATO_NONEXISTENT_FIELD_XYZ"
    os.environ.pop(env_key, None)

    value, key, is_complex = src.get_field_value(FieldInfo(), "nonexistent_field_xyz")
    assert value is None
    assert key == "nonexistent_field_xyz"
    assert is_complex is False


# ---------------------------------------------------------------------------
# get_field_value — secrets_cache path
# ---------------------------------------------------------------------------


def test_get_field_value_prefers_cache_over_env() -> None:
    """Populated secrets_cache takes precedence over environment variables."""
    from pydantic.fields import FieldInfo

    src = _make_source()
    src.secrets_cache = {"trading_mode": "live_from_cache"}
    os.environ["ZKSATO_TRADING_MODE"] = "paper_from_env"
    try:
        value, key, _ = src.get_field_value(FieldInfo(), "trading_mode")
        assert value == "live_from_cache"
    finally:
        os.environ.pop("ZKSATO_TRADING_MODE", None)
        src.secrets_cache = {}


# ---------------------------------------------------------------------------
# prepare_field_value — passthrough
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw", [None, "hello", 42, True, {"k": "v"}, [1, 2, 3]])
def test_prepare_field_value_is_transparent_passthrough(raw: object) -> None:
    """prepare_field_value must return the value unchanged for any input type."""
    from pydantic.fields import FieldInfo

    src = _make_source()
    result = src.prepare_field_value("any_field", FieldInfo(), raw, False)
    assert result is raw


# ---------------------------------------------------------------------------
# __call__ aggregation
# ---------------------------------------------------------------------------


def test_call_includes_fields_from_cache() -> None:
    """__call__ must include fields whose value comes from secrets_cache."""
    src = _make_source()
    src.secrets_cache = {"environment": "staging"}

    result = src()

    assert "environment" in result
    assert result["environment"] == "staging"


def test_call_excludes_fields_with_none_values() -> None:
    """__call__ must not include fields whose resolved value is None."""
    src = _make_source()
    # Ensure no env var leaks in for a nonsense field name
    os.environ.pop("ZKSATO_NONEXISTENT_XYZ", None)

    result = src()
    assert "nonexistent_xyz" not in result


def test_call_returns_dict_with_nonnull_values() -> None:
    """All values returned by __call__ must be non-None (absent fields are skipped)."""
    # Clear any stray ZKSATO_ vars that could interfere
    leaked = {k: v for k, v in os.environ.items() if k.startswith("ZKSATO_")}
    for k in leaked:
        del os.environ[k]
    try:
        from zksato.config import Settings

        src = AWSSecretManagerSettingsSource(Settings)
        result = src()
        assert isinstance(result, dict)
        assert all(v is not None for v in result.values())
    finally:
        os.environ.update(leaked)
