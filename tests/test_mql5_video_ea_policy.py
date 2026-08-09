from pathlib import Path


EA_PATH = Path("ea/ZKSATO_VideoDerived_PA_Grid.mq5")


def _source() -> str:
    return EA_PATH.read_text(encoding="utf-8")


def test_reference_ea_hard_blocks_real_accounts() -> None:
    source = _source()
    assert "ACCOUNT_TRADE_MODE_REAL" in source
    assert "return(INIT_FAILED);" in source
    assert "refuses real accounts" in source
    assert "AllowReal" not in source
    assert "EnableReal" not in source


def test_reference_ea_has_bounded_fixed_size_controls() -> None:
    source = _source()
    assert "InpLots" in source
    assert "InpMaxPositions" in source
    assert "InpMaxPendingOrders" in source
    assert "InpMaxCycleVolume" in source
    assert "InpBasketMaxLossCurrency" in source
    assert "InpCooldownSeconds" in source
    assert "volume_slots" in source
    assert "hard_slots" in source


def test_reference_ea_has_no_martingale_multiplier_inputs() -> None:
    source = _source().lower()
    forbidden = (
        "martingale",
        "lotmultiplier",
        "lot_multiplier",
        "recoverymultiplier",
        "recovery_multiplier",
    )
    for token in forbidden:
        assert token not in source
