import os
import io
import json
import logging
import math
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger("ai_analyzer")



def analyze_pnl_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Parses equity or F&O PnL dataframe and computes summary stats for AI context."""
    # Drop completely empty rows and columns
    df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)

    # Auto-detect header row if the first row isn't the header (common in broker Excel exports)
    def is_header_row(row_values):
        keywords = ['pnl', 'profit', 'realized', 'symbol', 'scrip', 'buy', 'sell', 'qty', 'quantity', 'charges', 'tax']
        text = " ".join([str(x).lower() for x in row_values])
        return sum(1 for k in keywords if k in text) >= 2

    if not is_header_row(df.columns):
        for i in range(min(20, len(df))):
            row_vals = df.iloc[i].values
            if is_header_row(row_vals):
                df.columns = row_vals
                df = df.iloc[i+1:].reset_index(drop=True)
                break

    # Filter out summary 'Total' rows often found at the bottom of broker exports
    if len(df.columns) > 0:
        df = df[~df.iloc[:, 0].astype(str).str.strip().str.lower().isin(["total", "grand total", "subtotal"])]

    # Normalize column headers
    df.columns = [
        str(col).strip().lower().replace(" ", "_") for col in df.columns
    ]

    # Smart column matching heuristic
    def find_col(keywords, exclude=None):
        for col in df.columns:
            if exclude and any(x in col for x in exclude):
                continue
            if any(k in col for k in keywords):
                return col
        return None
        
    col_map = {
        "pnl": find_col(["realized_p&l", "realized", "net_pnl", "net_profit", "pnl", "p&l", "profit"], exclude=["pct", "%", "unrealized"]),
        "pnl_pct": find_col(["realized_p&l_pct", "pct", "%"], exclude=["unrealized"]),
        "symbol": find_col(["symbol", "tradingsymbol", "scrip"]),
        "buy_val": find_col(["buy_value", "buy_amount"]),
        "sell_val": find_col(["sell_value", "sell_amount"]),
        "qty": find_col(["quantity", "qty"], exclude=["open"]),
        "date": find_col(["date", "time", "day"]),
        "strategy": find_col(["strategy", "setup"]),
        "emotion": find_col(["emotion"]),
        "notes": find_col(["notes", "reflection"])
    }

    if df.columns.duplicated().any():
        raise ValueError("Report contains duplicate column names.")

    def numeric_amounts(series, label):
        text = series.astype(str).str.strip().str.replace(",", "", regex=False).str.replace("₹", "", regex=False)
        text = text.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
        values = pd.to_numeric(text, errors="coerce")
        if values.isna().any() or not values.map(math.isfinite).all():
            raise ValueError(f"{label} values must be finite numbers.")
        return values

    pnl_col = col_map.get("pnl")
    if not pnl_col and col_map["buy_val"] and col_map["sell_val"]:
        df = df.copy()
        df["calculated_pnl"] = (numeric_amounts(df[col_map["sell_val"]], "Sell Value")
                                - numeric_amounts(df[col_map["buy_val"]], "Buy Value"))
        pnl_col = "calculated_pnl"
    if not pnl_col:
        raise ValueError("No PnL column or Buy Value / Sell Value columns found.")
    pnl_series = numeric_amounts(df[pnl_col], "PnL")
    if df.empty:
        raise ValueError("No trade rows found.")

    total_trades = len(df)
    net_pnl = float(pnl_series.sum())
    winning_trades = pnl_series[pnl_series > 0]
    losing_trades = pnl_series[pnl_series < 0]

    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0

    total_gains = float(winning_trades.sum())
    total_losses = abs(float(losing_trades.sum()))
    avg_profit_abs = float(total_gains / win_count) if win_count > 0 else 0.0
    avg_loss_abs = float(total_losses / loss_count) if loss_count > 0 else 0.0

    pnl_pct_col = col_map.get("pnl_pct")
    if pnl_pct_col:
        pnl_pct_series = pd.to_numeric(df[pnl_pct_col], errors="coerce").fillna(0)
    elif "buy_val" in col_map and col_map["buy_val"]:
        buy_series = pd.to_numeric(df[col_map["buy_val"]], errors="coerce").replace(0, pd.NA)
        pnl_pct_series = (pnl_series / buy_series * 100).fillna(0)
    else:
        pnl_pct_series = pd.Series(0.0, index=df.index)

    avg_profit_pct = float(pnl_pct_series[pnl_series > 0].mean()) if win_count > 0 else 0.0
    avg_loss_pct = float(pnl_pct_series[pnl_series < 0].mean()) if loss_count > 0 else 0.0

    # CE vs PE Analysis
    ce_pnl = 0.0
    pe_pnl = 0.0
    if "symbol" in col_map and col_map["symbol"]:
        sym_col = col_map["symbol"]
        is_ce = df[sym_col].astype(str).str.upper().str.endswith("CE")
        is_pe = df[sym_col].astype(str).str.upper().str.endswith("PE")
        ce_pnl = float(pnl_series[is_ce].sum())
        pe_pnl = float(pnl_series[is_pe].sum())

    # Day of Week Analysis
    best_day_win_rate = "N/A"
    worst_day_pnl = "N/A"
    date_col = col_map.get("date")
    if date_col:
        try:
            dates = pd.to_datetime(df[date_col], errors="coerce")
            valid_mask = dates.notna()
            if valid_mask.any():
                days = dates[valid_mask].dt.day_name()
                day_groups = pnl_series[valid_mask].groupby(days)
                
                win_rates = day_groups.apply(lambda x: (x > 0).mean() * 100)
                if not win_rates.empty:
                    best_day_win_rate = str(win_rates.idxmax())
                
                sum_pnl = day_groups.sum()
                if not sum_pnl.empty:
                    worst_day_pnl = str(sum_pnl.idxmin())
        except Exception as e:
            logger.warning(f"Failed to parse dates for day of week analysis: {e}")

    max_win = float(winning_trades.max()) if win_count > 0 else 0.0
    max_loss = float(losing_trades.min()) if loss_count > 0 else 0.0
    avg_trade = float(pnl_series.mean()) if total_trades > 0 else 0.0

    def clean_float(val):
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return 0.0
            return round(f, 2)
        except (ValueError, TypeError):
            return 0.0

    # Preserve normalized rows for deterministic analysis (no database insertion).
    parsed_trades = []
    for idx, row in df.iterrows():
        pnl = float(pnl_series.loc[idx])
        sym = str(row[col_map.get("symbol")]) if col_map.get("symbol") else "Unknown"
        qty_val = row[col_map.get("qty")] if col_map.get("qty") else 1
        try:
            qty = int(pd.to_numeric(qty_val, errors="coerce"))
        except:
            qty = 1
            
        date_str = str(row[date_col]) if date_col and pd.notna(row[date_col]) else None
        
        is_ce = sym.upper().endswith("CE")
        is_pe = sym.upper().endswith("PE")
        segment = "CE" if is_ce else ("PE" if is_pe else ("Futures" if sym.upper().endswith("FUT") else "Equity"))
        
        parsed_trades.append({
            "symbol": sym,
            "net_pnl": pnl,
            "quantity": qty,
            "date": date_str,
            "segment": segment,
            "strategy": str(row[col_map["strategy"]]) if col_map["strategy"] and pd.notna(row[col_map["strategy"]]) else None,
            "emotion": str(row[col_map["emotion"]]) if col_map["emotion"] and pd.notna(row[col_map["emotion"]]) else None,
            "has_notes": bool(col_map["notes"] and pd.notna(row[col_map["notes"]]) and str(row[col_map["notes"]]).strip())
        })

    return {
        "total_trades": total_trades,
        "net_pnl": clean_float(net_pnl),
        "gross_pnl": clean_float(net_pnl),
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": clean_float(win_rate),
        "avg_profit_abs": clean_float(avg_profit_abs),
        "avg_loss_abs": clean_float(avg_loss_abs),
        "avg_profit_pct": clean_float(avg_profit_pct),
        "avg_loss_pct": clean_float(avg_loss_pct),
        "ce_pnl": clean_float(ce_pnl),
        "pe_pnl": clean_float(pe_pnl),
        "best_day_win_rate": best_day_win_rate,
        "worst_day_pnl": worst_day_pnl,
        "max_win": clean_float(max_win),
        "max_loss": clean_float(max_loss),
        "avg_trade": clean_float(avg_trade),
        "parsed_trades": parsed_trades,
    }


def generate_ai_insights_from_csv(stats, raw_csv_preview=""):
    """Compatibility response generated locally; external calls require explicit selection."""
    from app.core.trade_review import build_review
    report = build_review([{'id': f'row_{i+1}', 'pnl': r['net_pnl'], 'symbol': r['symbol'],
                            'segment': r['segment'], 'date': None}
                           for i, r in enumerate(stats.get('parsed_trades', []))], source='upload')
    return legacy_insights(report)


def legacy_insights(report):
    return {'executive_summary': report['summary'],
            'strengths': [f['evidence'] for f in report['strengths']],
            'leakages': [f['evidence'] for f in report['weaknesses']],
            'actionable_recommendations': [p['action'] for p in report['action_plan']],
            'disclaimer': 'Descriptive review, not a forecast or a recommendation to buy or sell.'}
