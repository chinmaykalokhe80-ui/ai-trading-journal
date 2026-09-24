from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union

DEFAULT_CHARGES_CONFIG = [
    {
        "effective_from": "2024-10-01",
        "brokerage_flat": 20.0,
        "brokerage_pct": 0.0003,  # 0.03%
        "stt_options_sell_pct": 0.0010,  # 0.10% (Pre Budget 2026 rate for reference)
        "stt_options_exercise_pct": 0.00125,
        "stt_futures_sell_pct": 0.0002,  # 0.02%
        "stt_equity_delivery_pct": 0.001,  # 0.1% buy & sell
        "stt_equity_intraday_sell_pct": 0.00025,  # 0.025% sell side
        "exchange_txn_charge_pct": {
            "equity": 0.0000345,
            "futures": 0.00002,
            "options": 0.0005,
        },
        "gst_pct": 0.18,  # 18% on (brokerage + exchange txn charges)
        "sebi_charges_pct": 0.000001,  # ₹10 per crore (0.0001%)
        "stamp_duty_pct": {
            "equity": 0.00015,  # 0.015% buy side delivery
            "futures": 0.00002,  # 0.002% buy side
            "options": 0.00003,  # 0.003% buy side
        },
        "dp_charges_flat": 13.5,  # per scrip delivery sell side
    },
    {
        "effective_from": "2026-04-01",
        "brokerage_flat": 20.0,
        "brokerage_pct": 0.0003,  # 0.03%
        "stt_options_sell_pct": 0.0015,  # 0.15% (Union Budget 2026-27 updated rate)
        "stt_options_exercise_pct": 0.0015,  # 0.15%
        "stt_futures_sell_pct": 0.0005,  # 0.05%
        "stt_equity_delivery_pct": 0.001,  # 0.1% buy & sell
        "stt_equity_intraday_sell_pct": 0.00025,  # 0.025%
        "exchange_txn_charge_pct": {
            "equity": 0.0000345,
            "futures": 0.00002,
            "options": 0.0005,
        },
        "gst_pct": 0.18,
        "sebi_charges_pct": 0.000001,
        "stamp_duty_pct": {
            "equity": 0.00015,
            "futures": 0.00002,
            "options": 0.00003,
        },
        "dp_charges_flat": 13.5,
    },
]


@dataclass
class TradeLegInput:
    leg_id: str
    instrument: str
    segment: str  # "Equity", "Futures", "CE", "PE"
    side: str  # "buy", "sell"
    price: float
    quantity: int
    is_delivery: bool = False
    is_exercised: bool = False


@dataclass
class ChargesBreakdown:
    brokerage: float
    stt: float
    exchange_txn_charge: float
    gst: float
    sebi_charges: float
    stamp_duty: float
    dp_charges: float
    total_charges: float
    gross_pnl: float
    net_pnl: float


def get_applicable_config(
    trade_date: Union[date, datetime, str],
    configs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Finds the charges_config document with the latest effective_from <= trade_date."""
    if configs is None:
        configs = DEFAULT_CHARGES_CONFIG

    if isinstance(trade_date, str):
        trade_dt = datetime.strptime(trade_date[:10], "%Y-%m-%d").date()
    elif isinstance(trade_date, datetime):
        trade_dt = trade_date.date()
    else:
        trade_dt = trade_date

    sorted_configs = sorted(
        configs,
        key=lambda c: datetime.strptime(c["effective_from"], "%Y-%m-%d").date(),
    )

    applicable = sorted_configs[0]
    for cfg in sorted_configs:
        eff_dt = datetime.strptime(cfg["effective_from"], "%Y-%m-%d").date()
        if eff_dt <= trade_dt:
            applicable = cfg
        else:
            break

    return applicable


def calculate_trade_charges(
    legs: List[TradeLegInput],
    trade_date: Union[date, datetime, str],
    configs: Optional[List[Dict[str, Any]]] = None,
) -> ChargesBreakdown:
    """Computes charges breakdown, gross PnL, and net PnL for a list of legs in a trade."""
    cfg = get_applicable_config(trade_date, configs)

    brokerage = 0.0
    stt = 0.0
    exchange_txn_charge = 0.0
    sebi_charges = 0.0
    stamp_duty = 0.0
    dp_charges = 0.0

    buy_amount = 0.0
    sell_amount = 0.0

    # Track scrips for delivery sell side DP charges
    delivery_sell_scrips = set()

    for leg in legs:
        segment = leg.segment.upper()
        turnover = leg.price * leg.quantity
        side = leg.side.lower()

        if side == "buy":
            buy_amount += turnover
        else:
            sell_amount += turnover

        # 1. Brokerage
        if segment == "EQUITY" and leg.is_delivery:
            # Delivery equity brokerage is ₹0 or config flat if specified
            b_fee = 0.0
        elif segment in ("CE", "PE"):
            # Flat ₹20 per executed leg for options
            b_fee = cfg["brokerage_flat"]
        else:
            # Min(flat, pct * turnover)
            b_fee = min(cfg["brokerage_flat"], turnover * cfg["brokerage_pct"])

        brokerage += b_fee

        # 2. STT
        if segment == "EQUITY":
            if leg.is_delivery:
                # 0.1% on buy and sell
                stt += turnover * cfg["stt_equity_delivery_pct"]
            else:
                # Intraday: 0.025% on sell side only
                if side == "sell":
                    stt += turnover * cfg["stt_equity_intraday_sell_pct"]

        elif segment in ("CE", "PE"):
            if side == "sell":
                if leg.is_exercised:
                    stt += turnover * cfg["stt_options_exercise_pct"]
                else:
                    stt += turnover * cfg["stt_options_sell_pct"]

        elif segment == "FUTURES":
            if side == "sell":
                stt += turnover * cfg["stt_futures_sell_pct"]

        # 3. Exchange Txn Charge
        if segment in ("CE", "PE"):
            ex_rate = cfg["exchange_txn_charge_pct"]["options"]
        elif segment == "FUTURES":
            ex_rate = cfg["exchange_txn_charge_pct"]["futures"]
        else:
            ex_rate = cfg["exchange_txn_charge_pct"]["equity"]

        exchange_txn_charge += turnover * ex_rate

        # 4. SEBI Charges
        sebi_charges += turnover * cfg["sebi_charges_pct"]

        # 5. Stamp Duty (Buy side only)
        if side == "buy":
            if segment in ("CE", "PE"):
                sd_rate = cfg["stamp_duty_pct"]["options"]
            elif segment == "FUTURES":
                sd_rate = cfg["stamp_duty_pct"]["futures"]
            else:
                sd_rate = cfg["stamp_duty_pct"]["equity"]
            stamp_duty += turnover * sd_rate

        # 6. DP Charges (Equity delivery sell side)
        if segment == "EQUITY" and leg.is_delivery and side == "sell":
            delivery_sell_scrips.add(leg.instrument)

    dp_charges = len(delivery_sell_scrips) * cfg["dp_charges_flat"]

    # 7. GST (18% on brokerage + exchange txn charges)
    gst = (brokerage + exchange_txn_charge) * cfg["gst_pct"]

    total_charges = (
        brokerage
        + stt
        + exchange_txn_charge
        + gst
        + sebi_charges
        + stamp_duty
        + dp_charges
    )

    gross_pnl = sell_amount - buy_amount
    net_pnl = gross_pnl - total_charges

    return ChargesBreakdown(
        brokerage=round(brokerage, 2),
        stt=round(stt, 2),
        exchange_txn_charge=round(exchange_txn_charge, 2),
        gst=round(gst, 2),
        sebi_charges=round(sebi_charges, 2),
        stamp_duty=round(stamp_duty, 2),
        dp_charges=round(dp_charges, 2),
        total_charges=round(total_charges, 2),
        gross_pnl=round(gross_pnl, 2),
        net_pnl=round(net_pnl, 2),
    )
