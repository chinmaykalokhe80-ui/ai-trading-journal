import os
import io
import json
import logging
import pandas as pd
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger("ai_analyzer")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


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
        df = df[~df.iloc[:, 0].astype(str).str.contains("Total", case=False, na=False)]

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
        "pnl": find_col(["realized_p&l", "realized", "net_pnl", "net_profit", "pnl", "profit"], exclude=["pct", "%", "unrealized"]),
        "pnl_pct": find_col(["realized_p&l_pct", "pct", "%"], exclude=["unrealized"]),
        "symbol": find_col(["symbol", "tradingsymbol", "scrip"]),
        "buy_val": find_col(["buy_value", "buy_amount"]),
        "sell_val": find_col(["sell_value", "sell_amount"]),
        "qty": find_col(["quantity", "qty"], exclude=["open"]),
        "date": find_col(["date", "time", "day"])
    }

    pnl_col = col_map.get("pnl")

    # If net pnl column isn't directly named, compute from buy and sell value
    if not pnl_col and "buy_val" in col_map and "sell_val" in col_map:
        df["calculated_pnl"] = (
            pd.to_numeric(df[col_map["sell_val"]], errors="coerce").fillna(0)
            - pd.to_numeric(df[col_map["buy_val"]], errors="coerce").fillna(0)
        )
        pnl_col = "calculated_pnl"

    if pnl_col:
        pnl_series = pd.to_numeric(df[pnl_col], errors="coerce").fillna(0)
    else:
        # Fallback: take first numeric column as PnL or generate 0s
        numeric_cols = df.select_dtypes(include=["number"]).columns
        pnl_series = (
            df[numeric_cols[0]]
            if len(numeric_cols) > 0
            else pd.Series([0] * len(df))
        )

    logger.error(f"DEBUG_DF_COLUMNS: {list(df.columns)}")
    logger.error(f"DEBUG_COL_MAP: {col_map}")
    logger.error(f"DEBUG_PNL_COL: {pnl_col}")
    if len(df) > 0:
        logger.error(f"DEBUG_FIRST_ROW: {df.iloc[0].to_dict()}")

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
        pnl_pct_series = pd.Series([0.0]*len(df))

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

    max_win = float(pnl_series.max()) if total_trades > 0 else 0.0
    max_loss = float(pnl_series.min()) if total_trades > 0 else 0.0
    avg_trade = float(pnl_series.mean()) if total_trades > 0 else 0.0

    import math

    def clean_float(val):
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return 0.0
            return round(f, 2)
        except (ValueError, TypeError):
            return 0.0

    # Extract individual trades for db insertion
    parsed_trades = []
    for idx, row in df.iterrows():
        pnl = float(row[pnl_col]) if pnl_col and pd.notna(row[pnl_col]) else 0.0
        sym = str(row[col_map.get("symbol")]) if col_map.get("symbol") else "Unknown"
        qty_val = row[col_map.get("qty")] if col_map.get("qty") else 1
        try:
            qty = int(pd.to_numeric(qty_val, errors="coerce"))
        except:
            qty = 1
            
        date_str = str(row[date_col]) if date_col and pd.notna(row[date_col]) else None
        
        is_ce = sym.upper().endswith("CE")
        is_pe = sym.upper().endswith("PE")
        segment = "CE" if is_ce else ("PE" if is_pe else "Equity")
        
        parsed_trades.append({
            "symbol": sym,
            "net_pnl": pnl,
            "quantity": qty,
            "date": date_str,
            "segment": segment
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


def generate_ai_insights_from_csv(
    stats: Dict[str, Any], raw_csv_preview: str = ""
) -> Dict[str, Any]:
    """Generates AI insights via Gemini API or structured intelligent engine fallback."""
    api_key = os.getenv("GEMINI_API_KEY", "")

    prompt = f"""You are an elite Indian Equity & F&O Trading Coach analyzing a trader's uploaded PnL CSV report.
Here is the extracted performance data:
- Total Trades Executed: {stats['total_trades']}
- Net PnL: ₹{stats['net_pnl']}
- Win Rate: {stats['win_rate']}% ({stats['win_count']} Wins, {stats['loss_count']} Losses)
- Average Profit: ₹{stats['avg_profit_abs']} ({stats['avg_profit_pct']}%)
- Average Loss: ₹{stats['avg_loss_abs']} ({stats['avg_loss_pct']}%)
- Largest Single Winning Trade: ₹{stats['max_win']}
- Average Return Per Trade: ₹{stats['avg_trade']}
- Net PnL from Call Options (CE): ₹{stats['ce_pnl']}
- Net PnL from Put Options (PE): ₹{stats['pe_pnl']}
- Highest Probability of Profit Day: {stats['best_day_win_rate']}
- Maximum Loss Day: {stats['worst_day_pnl']}

Instructions:
1. Provide a concise, high-impact executive summary of their trading performance.
2. Identify 2 key strengths.
3. Identify 2 major leakages or behavioral red flags (e.g., asymmetric risk-reward where 1 bad loss wiped out multiple small wins, bias towards CE or PE causing massive losses, worst trading days).
4. Give 3 actionable, specific recommendations tailored for Indian Equity/F&O traders.
5. Include a clear disclaimer that this is behavioral analysis, not direct financial advice.

Format the output strictly as a JSON object with keys:
"executive_summary", "strengths" (array of strings), "leakages" (array of strings), "actionable_recommendations" (array of strings), "disclaimer"."""

    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"},
            }
            res = requests.post(url, json=payload, timeout=15)
            if res.status_code == 200:
                content = res.json()["candidates"][0]["content"]["parts"][0][
                    "text"
                ]
                return json.loads(content)
        except Exception as e:
            logger.warning(
                f"Gemini API call failed, falling back to rule-based analysis: {e}"
            )

    # Fallback Rule-Based AI Engine
    is_profitable = stats["net_pnl"] >= 0
    asymmetric_loss = abs(stats["avg_loss_abs"]) > (stats["avg_profit_abs"] * 1.5)

    strengths = []
    if stats["win_rate"] >= 50:
        strengths.append(
            f"Strong consistency with a {stats['win_rate']}% win rate across {stats['total_trades']} trades."
        )
    else:
        strengths.append(
            "Active trade logging discipline across Equity and F&O instruments."
        )

    if is_profitable:
        strengths.append(
            f"Net positive return of ₹{stats['net_pnl']} maintained after accounting for exchange taxes and STT."
        )
    else:
        strengths.append(
            f"Kept maximum single win capped at ₹{stats['max_win']}, showing profit taking ability."
        )

    leakages = []
    if asymmetric_loss:
        leakages.append(
            f"Asymmetric risk leakage: your largest single loss (₹{stats['max_loss']}) is significantly larger than your best win (₹{stats['max_win']}), indicating delayed stop loss execution."
        )

    if not leakages:
        leakages.append(
            "Over-trading risk during volatile session windows."
        )

    recommendations = [
        "Enforce strict 1:2 Risk-to-Reward parameters on entry so winning trades cover consecutive small stop-losses.",
        "Consolidate multiple option leg entries into single strategy orders to reduce per-order turnover tax drag.",
        "Set a hard daily stop-loss limit (e.g. 2x average loss) to prevent revenge trading after an early loss.",
    ]

    return {
        "executive_summary": (
            f"Analysis of your uploaded PnL CSV reveals a net return of ₹{stats['net_pnl']} across {stats['total_trades']} trades "
            f"with a {stats['win_rate']}% win rate, averaging ₹{stats['avg_profit_abs']} per win and ₹{stats['avg_loss_abs']} per loss. "
            + (
                "Your performance shows positive expectancy, but risk-reward execution can be further optimized."
                if is_profitable
                else "Your performance indicates tax drag and heavy loss tail risk impacting your bottom line."
            )
        ),
        "strengths": strengths,
        "leakages": leakages,
        "actionable_recommendations": recommendations,
        "disclaimer": "This AI analysis evaluates trading behavior, tax drag, and statistical distribution patterns. It does not constitute financial, investment, or tax filing advice.",
    }
