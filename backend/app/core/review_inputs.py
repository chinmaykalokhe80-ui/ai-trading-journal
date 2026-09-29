"""Adapters keep unknown/synthetic timestamps and multi-leg risk out of metrics."""
import pandas as pd
from app.core.ai_analyzer import analyze_pnl_dataframe

PLACEHOLDERS = {'csv upload', 'manual ingestion', 'manual trade', 'unassigned', 'unknown', 'neutral', ''}


def tag(value):
    value = str(value or '').strip()
    return None if value.lower() in PLACEHOLDERS else value


def parse_date(value):
    if not value:
        return None
    try:
        date = pd.Timestamp(value)
        if pd.isna(date):
            return None
        if date.tzinfo:
            date = date.tz_convert('Asia/Kolkata').tz_localize(None)
        return date.to_pydatetime()
    except (ValueError, TypeError, OverflowError):
        return None


def uploaded_rows(df):
    stats = analyze_pnl_dataframe(df)
    parsed = stats.pop('parsed_trades')
    rows = [{'id': f'row_{i+1}', 'pnl': r['net_pnl'], 'symbol': r['symbol'],
             'segment': r['segment'], 'date': parse_date(r['date']),
             'strategy': tag(r.get('strategy')), 'emotion': tag(r.get('emotion')),
             'has_notes': r.get('has_notes', False)} for i, r in enumerate(parsed)]
    return rows, stats


def journal_rows(trades):
    rows = []
    excluded = 0
    for trade in trades:
        if trade.status != 'closed':
            excluded += 1
            continue
        legs = trade.legs
        synthetic = not legs or any(l.price <= 0 for l in legs)
        # Manual records currently use insertion time for both entry and exit.
        known_date = not synthetic and trade.exit_time and trade.exit_time != trade.entry_time
        risk = None
        ordered = sorted(legs, key=lambda l: l.fill_time)
        if len(ordered) == 2 and not synthetic and trade.planned_stop_loss is not None:
            first, last = ordered
            same = first.instrument.upper() == last.instrument.upper() and first.segment == last.segment
            if same and first.side != last.side and first.quantity == last.quantity:
                distance = (first.price-trade.planned_stop_loss if first.side == 'buy'
                            else trade.planned_stop_loss-first.price)
                if distance > 0:
                    risk = distance*first.quantity
        segments = {l.segment for l in legs}
        rows.append({'id': trade.id, 'pnl': float(trade.gross_pnl),
                     'symbol': ', '.join(dict.fromkeys(l.instrument for l in legs)) or 'Unknown',
                     'segment': next(iter(segments)) if len(segments) == 1 else 'Mixed',
                     'date': trade.exit_time if known_date else None,
                     'strategy': tag(trade.strategy_tag), 'emotion': tag(trade.emotion_tag),
                     'has_notes': bool((trade.notes or '').strip()),
                     'has_stop': trade.planned_stop_loss is not None,
                     'planned_risk': risk})
    return rows, excluded
