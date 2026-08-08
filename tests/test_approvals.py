from zksato.approvals import ApprovalRepository, order_fingerprint
from zksato.domain import OrderIntent, Side


def test_live_approval_is_intent_bound_one_time_and_four_eyes() -> None:
    repository = ApprovalRepository()
    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        price=40,
        stop_loss=38,
        client_order_id="live-1",
    )
    approval = repository.create(intent, created_by="risk-a", ttl_seconds=120)
    assert approval.fingerprint == order_fingerprint(intent)
    consumed = repository.consume(
        str(approval.id),
        intent,
        consumed_by="operator-b",
        require_distinct_approver=True,
    )
    assert consumed.consumed_by == "operator-b"

    try:
        repository.consume(
            str(approval.id),
            intent,
            consumed_by="operator-c",
            require_distinct_approver=True,
        )
    except ValueError as exc:
        assert "already consumed" in str(exc)
    else:
        raise AssertionError("approval must be one-time")


def test_four_eyes_rejects_same_actor() -> None:
    repository = ApprovalRepository()
    intent = OrderIntent(
        symbol="PTT",
        side=Side.BUY,
        quantity=100,
        price=30,
        stop_loss=28,
    )
    approval = repository.create(intent, created_by="operator-a", ttl_seconds=120)
    try:
        repository.consume(
            str(approval.id),
            intent,
            consumed_by="operator-a",
            require_distinct_approver=True,
        )
    except ValueError as exc:
        assert "distinct approver" in str(exc)
    else:
        raise AssertionError("four-eyes policy must reject same actor")
