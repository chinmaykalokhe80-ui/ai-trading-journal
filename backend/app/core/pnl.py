"""Realized execution P&L without brokerage or tax deductions."""
from typing import Iterable, Protocol


class Execution(Protocol):
    instrument: str
    segment: str
    side: str
    price: float
    quantity: int


def calculate_realized_pnl(legs: Iterable[Execution]) -> float:
    """Match chronological executions FIFO; leave unmatched quantities unrealized."""
    from collections import defaultdict, deque
    positions = defaultdict(deque)
    gross_pnl = 0.0
    for leg in legs:
        queue = positions[(leg.instrument.strip().upper(), leg.segment.upper())]
        remaining = leg.quantity
        direction = 1 if leg.side.lower() == "buy" else -1
        while remaining and queue and queue[0][0] != direction:
            old_direction, old_price, old_qty = queue[0]
            matched = min(remaining, old_qty)
            gross_pnl += (leg.price - old_price) * matched * old_direction
            remaining -= matched
            old_qty -= matched
            if old_qty:
                queue[0] = (old_direction, old_price, old_qty)
            else:
                queue.popleft()
        if remaining:
            queue.append((direction, leg.price, remaining))
    return round(gross_pnl, 2)
