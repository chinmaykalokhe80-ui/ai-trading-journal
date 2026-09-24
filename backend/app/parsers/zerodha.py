import io
import uuid
import re
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.parsers.base import BrokerParser, ParsedTrade, ParsedLeg, ParsedFill
from app.core.charges_engine import calculate_trade_charges, TradeLegInput


def infer_segment_and_details(symbol: str, raw_segment: str = "") -> tuple:
    """Infers segment (Equity, Futures, CE, PE), underlying instrument name, and lot size."""
    sym_upper = symbol.strip().upper()

    # Options match: e.g. "NIFTY24MAY24000CE", "BANKNIFTY 48000 CE", "NIFTY 24000 CE"
    if " CE" in sym_upper or sym_upper.endswith("CE"):
        return "CE", sym_upper, 25
    elif " PE" in sym_upper or sym_upper.endswith("PE"):
        return "PE", sym_upper, 25

    # Futures match
    if " FUT" in sym_upper or sym_upper.endswith("FUT"):
        return "Futures", sym_upper, 25

    # Check FO raw segment
    if raw_segment.upper() in ("FO", "NFO", "BFO"):
        if sym_upper.endswith("CE"):
            return "CE", sym_upper, 25
        elif sym_upper.endswith("PE"):
            return "PE", sym_upper, 25
        return "Futures", sym_upper, 25

    return "Equity", sym_upper, 1


class ZerodhaConsoleParser(BrokerParser):

    def parse_csv(
        self, file_content: bytes, user_id: str = "single_user"
    ) -> List[ParsedTrade]:
        # Handle string or bytes content
        if isinstance(file_content, bytes):
            text_content = file_content.decode("utf-8-sig")
        else:
            text_content = file_content

        df = pd.read_csv(io.StringIO(text_content))

        # Normalize column names
        df.columns = [
            str(col).strip().lower().replace(" ", "_") for col in df.columns
        ]

        # Column mapping aliases
        col_map = {}
        for col in df.columns:
            if "symbol" in col or "tradingsymbol" in col:
                col_map["symbol"] = col
            elif "trade_date" in col or "date" in col:
                col_map["date"] = col
            elif "order_id" in col:
                col_map["order_id"] = col
            elif "trade_id" in col:
                col_map["trade_id"] = col
            elif "type" in col or "transaction" in col or "buy_sell" in col:
                col_map["side"] = col
            elif "quantity" in col or "qty" in col:
                col_map["quantity"] = col
            elif "price" in col or "rate" in col:
                col_map["price"] = col
            elif "segment" in col:
                col_map["segment"] = col

        parsed_fills: List[ParsedFill] = []

        for idx, row in df.iterrows():
            symbol = str(row.get(col_map.get("symbol", "symbol"), "UNKNOWN"))
            raw_segment = str(row.get(col_map.get("segment", "segment"), ""))
            segment, instrument, lot_size = infer_segment_and_details(
                symbol, raw_segment
            )

            side_raw = str(
                row.get(col_map.get("side", "side"), "buy")
            ).lower()
            side = "buy" if "b" in side_raw else "sell"

            qty = int(abs(float(row.get(col_map.get("quantity", "quantity"), 1))))
            price = float(row.get(col_map.get("price", "price"), 0.0))

            date_str = str(row.get(col_map.get("date", "date"), ""))
            try:
                if len(date_str) > 10:
                    fill_time = datetime.strptime(
                        date_str[:19], "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    fill_time = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except Exception:
                fill_time = datetime.now()

            order_id = str(
                row.get(col_map.get("order_id", "order_id"), f"ord_{idx}")
            )
            trade_id = str(
                row.get(col_map.get("trade_id", "trade_id"), f"trd_{idx}")
            )

            fill = ParsedFill(
                fill_id=f"fill_{uuid.uuid4().hex[:8]}",
                order_id=order_id,
                trade_id=trade_id,
                symbol=symbol,
                segment=segment,
                side=side,
                quantity=qty,
                price=price,
                fill_time=fill_time,
                is_delivery=(segment == "Equity"),
            )
            parsed_fills.append(fill)

        # Group fills by order_id to form legs
        fills_by_order: Dict[str, List[ParsedFill]] = {}
        for fill in parsed_fills:
            fills_by_order.setdefault(fill.order_id, []).append(fill)

        legs: List[ParsedLeg] = []
        for order_id, order_fills in fills_by_order.items():
            first_fill = order_fills[0]
            total_qty = sum(f.quantity for f in order_fills)
            weighted_price = (
                sum(f.price * f.quantity for f in order_fills) / total_qty
                if total_qty > 0
                else 0.0
            )

            leg = ParsedLeg(
                leg_id=f"leg_{uuid.uuid4().hex[:8]}",
                instrument=first_fill.symbol,
                segment=first_fill.segment,
                side=first_fill.side,
                price=weighted_price,
                quantity=total_qty,
                lot_size=25 if first_fill.segment != "Equity" else 1,
                order_id=order_id,
                fill_time=first_fill.fill_time,
                is_delivery=first_fill.is_delivery,
                fills=order_fills,
            )
            legs.append(leg)

        # Group legs by instrument into trades
        legs_by_instrument: Dict[str, List[ParsedLeg]] = {}
        for leg in legs:
            legs_by_instrument.setdefault(leg.instrument, []).append(leg)

        trades: List[ParsedTrade] = []

        for inst, inst_legs in legs_by_instrument.items():
            # Pair buy and sell legs
            sorted_legs = sorted(inst_legs, key=lambda l: l.fill_time)

            trade_engine_legs = [
                TradeLegInput(
                    leg_id=leg.leg_id,
                    instrument=leg.instrument,
                    segment=leg.segment,
                    side=leg.side,
                    price=leg.price,
                    quantity=leg.quantity,
                    is_delivery=leg.is_delivery,
                )
                for leg in sorted_legs
            ]

            trade_date = sorted_legs[0].fill_time
            charges_res = calculate_trade_charges(
                trade_engine_legs, trade_date=trade_date
            )

            trade_fills = []
            for leg in sorted_legs:
                if leg.fills:
                    trade_fills.extend(leg.fills)

            entry_time = sorted_legs[0].fill_time
            exit_time = sorted_legs[-1].fill_time if len(sorted_legs) > 1 else None

            trade = ParsedTrade(
                trade_id=f"trade_{uuid.uuid4().hex[:10]}",
                strategy_id=None,
                strategy_tag="Manual Ingestion",
                entry_time=entry_time,
                exit_time=exit_time,
                instrument=inst,
                segment=sorted_legs[0].segment,
                gross_pnl=charges_res.gross_pnl,
                total_charges=charges_res.total_charges,
                net_pnl=charges_res.net_pnl,
                status="closed" if exit_time else "open",
                legs=sorted_legs,
                fills=trade_fills,
            )
            trades.append(trade)

        return trades
