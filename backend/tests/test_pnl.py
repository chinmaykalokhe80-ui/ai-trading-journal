from types import SimpleNamespace
import pytest
from app.core.pnl import calculate_realized_pnl


@pytest.mark.parametrize("segment,buy,sell,quantity,expected", [
    ("Equity", 2500, 2600, 100, 10000),
    ("CE", 40, 120, 50, 4000),
    ("Futures", 50000, 50500, 25, 12500),
])
def test_pnl_without_deductions(segment, buy, sell, quantity, expected):
    legs = [SimpleNamespace(instrument="ABC", segment=segment, side=side, price=price, quantity=quantity)
            for side, price in [("buy", buy), ("sell", sell)]]
    assert calculate_realized_pnl(legs) == expected
