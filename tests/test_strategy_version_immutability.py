import pytest

from zksato.domain import StrategyVersion
from zksato.persistence import SqlStateStore
from zksato.store import StateStore


def _version(*, code_hash: str, fast_period: int) -> StrategyVersion:
    return StrategyVersion(
        name="ema_cross",
        version="v1",
        config={"fast_period": fast_period, "slow_period": 20},
        code_hash=code_hash,
    )


def test_memory_strategy_version_is_idempotent_but_immutable() -> None:
    store = StateStore()
    first = _version(code_hash="aaaaaaaa", fast_period=5)
    equivalent = _version(code_hash="aaaaaaaa", fast_period=5)

    stored = store.add_strategy_version(first)
    repeated = store.add_strategy_version(equivalent)

    assert repeated.id == stored.id
    assert len(store.list_strategy_versions()) == 1

    with pytest.raises(ValueError, match="immutable"):
        store.add_strategy_version(_version(code_hash="bbbbbbbb", fast_period=8))


def test_sql_strategy_version_identity_survives_restart(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'strategy.db'}"
    first = SqlStateStore(database_url)
    original = first.add_strategy_version(_version(code_hash="aaaaaaaa", fast_period=5))
    first.close()

    restarted = SqlStateStore(database_url)
    try:
        equivalent = restarted.add_strategy_version(_version(code_hash="aaaaaaaa", fast_period=5))
        assert equivalent.id == original.id
        with pytest.raises(ValueError, match="immutable"):
            restarted.add_strategy_version(_version(code_hash="cccccccc", fast_period=13))
    finally:
        restarted.close()
