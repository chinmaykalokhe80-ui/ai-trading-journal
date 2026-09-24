from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ParsedFill:
    fill_id: str
    order_id: str
    trade_id: str
    symbol: str
    segment: str  # "Equity", "Futures", "CE", "PE"
    side: str  # "buy", "sell"
    quantity: int
    price: float
    fill_time: datetime
    is_delivery: bool = False


@dataclass
class ParsedLeg:
    leg_id: str
    instrument: str
    segment: str
    side: str
    price: float
    quantity: int
    lot_size: int
    order_id: str
    fill_time: datetime
    is_delivery: bool = False
    fills: List[ParsedFill] = None


@dataclass
class ParsedTrade:
    trade_id: str
    strategy_id: Optional[str]
    strategy_tag: Optional[str]
    entry_time: datetime
    exit_time: Optional[datetime]
    instrument: str
    segment: str
    gross_pnl: float
    total_charges: float
    net_pnl: float
    status: str
    legs: List[ParsedLeg]
    fills: List[ParsedFill]


class BrokerParser(ABC):

    @abstractmethod
    def parse_csv(
        self, file_content: bytes, user_id: str = "single_user"
    ) -> List[ParsedTrade]:
        """Parses raw CSV bytes from a broker export into a list of ParsedTrade objects."""
        pass
