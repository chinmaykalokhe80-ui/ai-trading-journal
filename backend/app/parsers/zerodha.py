import io
import uuid
import re
import hashlib
import json
import math
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.parsers.base import BrokerParser, ParsedTrade, ParsedLeg, ParsedFill
from app.core.pnl import calculate_realized_pnl


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
            elif col in ("trade_type", "transaction_type", "buy_sell", "side", "type"):
                col_map["side"] = col
            elif "quantity" in col or "qty" in col:
                col_map["quantity"] = col
            elif "price" in col or "rate" in col:
                col_map["price"] = col
            elif "segment" in col:
                col_map["segment"] = col

        required = {"symbol", "date", "side", "quantity", "price"}
        missing = required - col_map.keys()
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
        if df.empty:
            raise ValueError("Tradebook contains no trades.")
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
            side = {"b": "buy", "s": "sell", "buy": "buy", "sell": "sell"}.get(side_raw.strip())
            if side is None:
                raise ValueError(f"Row {idx + 2}: invalid trade side")

            qty_raw = float(row[col_map["quantity"]])
            if not math.isfinite(qty_raw) or qty_raw <= 0 or not qty_raw.is_integer():
                raise ValueError(f"Row {idx + 2}: quantity must be a positive integer")
            qty = int(qty_raw)
            price = float(row.get(col_map.get("price", "price"), 0.0))

            if not math.isfinite(price) or price <= 0 or pd.isna(row[col_map["symbol"]]):
                raise ValueError(f"Row {idx + 2}: invalid price or symbol")
            symbol = symbol.strip().upper()
            if not symbol:
                raise ValueError(f"Row {idx + 2}: symbol is required")
            date_str = str(row.get(col_map.get("date", "date"), ""))
            try:
                if len(date_str) > 10:
                    fill_time = datetime.strptime(
                        date_str[:19], "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    fill_time = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError(f"Row {idx + 2}: invalid trade date") from exc

            order_id = str(
                row.get(col_map.get("order_id", "order_id"), f"ord_{idx}")
            )
            trade_id = str(
                row.get(col_map.get("trade_id", "trade_id"), f"trd_{idx}")
            )

            identity = json.dumps([user_id, trade_id, order_id, symbol, segment, side, qty, price, fill_time.isoformat()])
            fill = ParsedFill(
                fill_id="fill_" + hashlib.sha256(identity.encode()).hexdigest(),
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
            if any(existing.fill_id == fill.fill_id for existing in parsed_fills):
                raise ValueError(f"Row {idx + 2}: duplicate execution in file")
            parsed_fills.append(fill)

        # Group fills by order_id to form legs
        fills_by_order: Dict[str, List[ParsedFill]] = {}
        for fill in parsed_fills:
            fills_by_order.setdefault((fill.order_id, fill.symbol, fill.segment, fill.side), []).append(fill)

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
                order_id=first_fill.order_id,
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

            pnl = calculate_realized_pnl(sorted_legs)

            trade_fills = []
            for leg in sorted_legs:
                if leg.fills:
                    trade_fills.extend(leg.fills)

            entry_time = sorted_legs[0].fill_time
            balance = sum(l.quantity if l.side == "buy" else -l.quantity for l in sorted_legs)
            exit_time = sorted_legs[-1].fill_time if balance == 0 else None

            trade = ParsedTrade(
                trade_id="trade_" + hashlib.sha256("|".join(sorted(f.fill_id for f in trade_fills)).encode()).hexdigest(),
                strategy_id=None,
                strategy_tag="Manual Ingestion",
                entry_time=entry_time,
                exit_time=exit_time,
                instrument=inst,
                segment=sorted_legs[0].segment,
                gross_pnl=pnl,
                total_charges=0.0,
                net_pnl=pnl,
                status="closed" if exit_time else "open",
                legs=sorted_legs,
                fills=trade_fills,
            )
            trades.append(trade)

        return trades
