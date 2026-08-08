from zksato.security import redact_sensitive
from zksato.store import StateStore


def test_audit_hash_chain_detects_tampering() -> None:
    store = StateStore()
    store.add_audit("one", "first", {"symbol": "AOT"})
    store.add_audit("two", "second", {"symbol": "PTT"})
    assert store.verify_audit_chain() is True
    store.audit[0].data["symbol"] = "MUTATED"
    assert store.verify_audit_chain() is False


def test_redaction_removes_nested_secrets() -> None:
    payload = {
        "pin": "123456",
        "nested": {"app_secret": "secret", "symbol": "AOT"},
        "tokenValue": "abc",
    }
    redacted = redact_sensitive(payload)
    assert redacted["pin"] == "[REDACTED]"
    assert redacted["nested"]["app_secret"] == "[REDACTED]"
    assert redacted["nested"]["symbol"] == "AOT"
    assert redacted["tokenValue"] == "[REDACTED]"
