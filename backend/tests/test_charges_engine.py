import pytest
from app.core.charges_engine import (
    calculate_trade_charges,
    TradeLegInput,
    get_applicable_config,
)


def test_equity_delivery_charges():
    # Buy 100 RELIANCE @ 2500, Sell @ 2600
    legs = [
        TradeLegInput(
            leg_id="leg_1",
            instrument="RELIANCE",
            segment="Equity",
            side="buy",
            price=2500.0,
            quantity=100,
            is_delivery=True,
        ),
        TradeLegInput(
            leg_id="leg_2",
            instrument="RELIANCE",
            segment="Equity",
            side="sell",
            price=2600.0,
            quantity=100,
            is_delivery=True,
        ),
    ]

    res = calculate_trade_charges(legs, trade_date="2026-05-01")

    assert res.gross_pnl == 10000.0
    # Check net PnL matches within ₹1 tolerance
    expected_net_pnl = 9417.72
    assert abs(res.net_pnl - expected_net_pnl) <= 1.0


def test_option_sell_charges():
    # Sell 50 NIFTY 24000 CE @ 120, Buy @ 40
    legs = [
        TradeLegInput(
            leg_id="leg_1",
            instrument="NIFTY 24000 CE",
            segment="CE",
            side="sell",
            price=120.0,
            quantity=50,
        ),
        TradeLegInput(
            leg_id="leg_2",
            instrument="NIFTY 24000 CE",
            segment="CE",
            side="buy",
            price=40.0,
            quantity=50,
        ),
    ]

    res = calculate_trade_charges(legs, trade_date="2026-05-01")

    assert res.gross_pnl == 4000.0
    expected_net_pnl = 3939.01
    assert abs(res.net_pnl - expected_net_pnl) <= 1.0


def test_futures_charges():
    # Buy 25 BANKNIFTY FUT @ 50000, Sell @ 50500
    legs = [
        TradeLegInput(
            leg_id="leg_1",
            instrument="BANKNIFTY FUT",
            segment="Futures",
            side="buy",
            price=50000.0,
            quantity=25,
        ),
        TradeLegInput(
            leg_id="leg_2",
            instrument="BANKNIFTY FUT",
            segment="Futures",
            side="sell",
            price=50500.0,
            quantity=25,
        ),
    ]

    res = calculate_trade_charges(legs, trade_date="2026-05-01")

    assert res.gross_pnl == 12500.0
    expected_net_pnl = 11734.74
    assert abs(res.net_pnl - expected_net_pnl) <= 1.0


def test_versioned_config_lookup():
    # Date prior to 2026 budget effective date uses 2024 config
    cfg_2024 = get_applicable_config("2025-01-01")
    assert cfg_2024["stt_options_sell_pct"] == 0.0010

    # Date after 2026-04-01 uses 2026 config
    cfg_2026 = get_applicable_config("2026-05-01")
    assert cfg_2026["stt_options_sell_pct"] == 0.0015
