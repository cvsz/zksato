from zksato.persistence import SqlStateStore
from zksato.store import StateStore


def test_in_memory_runtime_state_is_defensively_copied() -> None:
    store = StateStore()
    payload = {"snapshot": {"state": "active", "fired": ["aot-buy-1"]}}

    store.save_runtime_state("video-ea:AOT", payload)
    payload["snapshot"]["fired"].append("mutated-after-save")

    assert store.get_runtime_state("video-ea:AOT") == {
        "snapshot": {"state": "active", "fired": ["aot-buy-1"]}
    }

    recovered = store.get_runtime_state("video-ea:AOT")
    assert recovered is not None
    recovered["snapshot"]["fired"].append("mutated-after-read")
    assert store.get_runtime_state("video-ea:AOT")["snapshot"]["fired"] == ["aot-buy-1"]

    assert store.delete_runtime_state("video-ea:AOT") is True
    assert store.get_runtime_state("video-ea:AOT") is None


def test_sql_runtime_state_survives_store_restart(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-state.db'}"
    first = SqlStateStore(database_url)
    first.save_runtime_state(
        "video-ea:AOT",
        {"snapshot": {"state": "active", "fired": ["aot-buy-1"]}},
    )
    first.close()

    restarted = SqlStateStore(database_url)
    try:
        assert restarted.get_runtime_state("video-ea:AOT") == {
            "snapshot": {"state": "active", "fired": ["aot-buy-1"]}
        }
    finally:
        restarted.close()
