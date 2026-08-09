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


def test_reference_ea_normalizes_symbol_volume_and_trade_constraints() -> None:
    source = _source()
    for token in (
        "SYMBOL_VOLUME_STEP",
        "SYMBOL_VOLUME_MIN",
        "SYMBOL_VOLUME_MAX",
        "SYMBOL_TRADE_STOPS_LEVEL",
        "SYMBOL_TRADE_FREEZE_LEVEL",
        "NormalizeVolume",
        "TradeResultOK",
        "ResultRetcode",
    ):
        assert token in source


def test_reference_ea_is_restart_safe_and_session_bounded() -> None:
    source = _source()
    for token in (
        "ACCOUNT_MARGIN_MODE",
        "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING",
        "ORDER_TIME_SPECIFIED",
        "SessionOpen",
        "RebuildStateFromTerminal",
        "HasPendingComment",
        "TesterStatistics",
        "STAT_PROFIT",
    ):
        assert token in source


def test_reference_ea_fails_closed_on_foreign_netting_exposure() -> None:
    source = _source()
    assert "NettingExposureCompatible" in source
    assert "if(!NettingExposureCompatible())" in source
    assert "cannot safely manage netting exposure" in source


def test_reference_ea_has_strategy_tester_presets() -> None:
    for path in (
        Path("ea/presets/ZKSATO_VideoDerived_PA_Grid_SET.set"),
        Path("ea/presets/ZKSATO_VideoDerived_PA_Grid_TFEX_RESEARCH.set"),
    ):
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "InpLots=" in content
        assert "InpMaxCycleVolume=" in content
