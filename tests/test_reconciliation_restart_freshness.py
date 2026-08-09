from datetime import UTC, datetime

from zksato.persistence import SqlStateStore, runtime_state_table


def test_sql_reconciliation_readiness_is_restart_local(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'state.db'}"

    first = SqlStateStore(database_url)
    try:
        assert first.broker_reconciliation_ready() is False
        first.set_broker_reconciliation_ready(True)
        assert first.broker_reconciliation_ready() is True
    finally:
        first.close()

    restarted = SqlStateStore(database_url)
    try:
        assert restarted.broker_reconciliation_ready() is False
        restarted.set_broker_reconciliation_ready(True)
        assert restarted.broker_reconciliation_ready() is True
    finally:
        restarted.close()


def test_legacy_persisted_reconciliation_state_is_ignored(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    first = SqlStateStore(database_url)
    try:
        first._upsert_payload(  # noqa: SLF001 - explicit legacy-state regression fixture
            runtime_state_table,
            runtime_state_table.c.key,
            "broker_reconciliation_ready",
            {
                "key": "broker_reconciliation_ready",
                "payload": {"ready": True},
                "updated_at": datetime.now(UTC),
            },
        )
    finally:
        first.close()

    restarted = SqlStateStore(database_url)
    try:
        assert restarted.broker_reconciliation_ready() is False
    finally:
        restarted.close()
