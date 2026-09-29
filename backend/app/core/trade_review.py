"""Deterministic coaching: measured outcomes are separate from behavioral hypotheses."""
from collections import defaultdict
from datetime import datetime
from math import sqrt, isfinite

BOOKS = [
    {"id": "probabilities", "title": "Trading in the Zone", "author": "Mark Douglas",
     "url": "https://www.penguinrandomhouse.com/books/350665/trading-in-the-zone-by-mark-douglas/",
     "principle": "Evaluate a repeatable process over a sample; one outcome does not establish an edge."},
    {"id": "risk", "title": "The New Trading for a Living", "author": "Alexander Elder",
     "url": "https://www.wiley-vch.de/en/areas-interest/finance-economics-law/the-new-trading-for-a-living-978-1-118-44392-7",
     "principle": "Define risk and keep records that connect the plan, execution, and result."},
    {"id": "practice", "title": "The Daily Trading Coach", "author": "Brett N. Steenbarger",
     "url": "https://catalogimages.wiley.com/images/db/pdf/9780470398562.excerpt.pdf",
     "principle": "Use specific review exercises and measure improvement in behavior, not just profit."},
]


def money(value):
    return round(float(value), 2)


def metrics(rows):
    values = [r['pnl'] for r in rows]
    wins = [v for v in values if v > 0]
    losses = [-v for v in values if v < 0]
    n = len(values)
    gains, loss = sum(wins), sum(losses)
    avg_win = gains / len(wins) if wins else None
    avg_loss = loss / len(losses) if losses else None
    p = len(wins) / n if n else 0
    # Wilson interval: descriptive approximation; clustered trades violate independence.
    z = 1.96
    denominator = 1 + z*z/n if n else 1
    center = (p + z*z/(2*n))/denominator if n else 0
    margin = z*sqrt(p*(1-p)/n + z*z/(4*n*n))/denominator if n else 0
    return {
        'count': n, 'pnl': money(sum(values)), 'wins': len(wins), 'losses': len(losses),
        'breakeven': n-len(wins)-len(losses), 'win_rate': money(100*p),
        'win_rate_interval': [money(100*max(0, center-margin)), money(100*min(1, center+margin))] if n else None,
        'expectancy': money(sum(values)/n) if n else None,
        'profit_factor': round(gains/loss, 3) if loss else None,
        'average_win': money(avg_win) if avg_win is not None else None,
        'average_loss': money(avg_loss) if avg_loss is not None else None,
        'payoff_ratio': round(avg_win/avg_loss, 3) if avg_win is not None and avg_loss else None,
        'break_even_win_rate': money(100*avg_loss/(avg_win+avg_loss)) if avg_win is not None and avg_loss else None,
        'largest_win': money(max(wins, default=0)), 'largest_loss': money(max(losses, default=0)),
        'winning_pnl': money(gains), 'losing_pnl': money(loss),
        'pnl_without_best': money(sum(values)-max(wins, default=0)),
        'top_winner_share': money(100*max(wins)/gains) if gains else None,
    }


def build_review(rows, source='journal', excluded_open=0):
    if not rows:
        raise ValueError('No closed trade records are available to analyze. Import trades or upload a P&L report.')
    if any(not isfinite(float(r['pnl'])) for r in rows):
        raise ValueError('P&L must contain only finite numbers.')
    m = metrics(rows)
    n = len(rows)
    limitations = [
        'Outcomes do not establish intent, FOMO, revenge trading, or whether a stop was followed.',
        'No tax or brokerage is calculated. Uploaded P&L is used as reported.',
        'Review thresholds (30 records; 5 per subgroup; 50% outcome concentration; average loss >1.5× average win) are app heuristics, not book rules or proof of an edge.',
        'Win-rate interval is a 95% Wilson approximation; correlated trades and changing market conditions reduce its usefulness.',
    ]
    if source == 'upload':
        limitations.append('Report rows may aggregate many executions. Counts describe rows, not verified round trips.')
    if source == 'journal':
        limitations.append('Imported journal records may group multiple round trips by instrument; counts are journal records.')
    if n < 30:
        limitations.append(f'Only {n} records: observations are preliminary; do not treat subgroup rankings as durable advantages.')
    dates = [r.get('date') for r in rows]
    reliable_dates = all(d is not None for d in dates)
    sequence_known = reliable_dates and len(set(dates)) == n
    daily = []
    curve = []
    max_drawdown = max_win_streak = max_loss_streak = None
    if reliable_dates:
        grouped = defaultdict(list)
        for row in rows:
            grouped[row['date'].date().isoformat()].append(row)
        daily = [{'date': day, **metrics(grouped[day])} for day in sorted(grouped)]
        cumulative = peak = drawdown = 0.0
        for day in daily:
            cumulative += day['pnl']
            peak = max(peak, cumulative)
            drawdown = max(drawdown, peak-cumulative)
            curve.append({'date': day['date'], 'pnl': money(cumulative)})
        max_drawdown = money(drawdown)
        limitations.append('Drawdown uses daily cumulative realized P&L from zero; it is not account-equity or intraday drawdown.')
    else:
        limitations.append('Missing or synthetic dates: daily patterns, drawdown, and chronological streaks are unavailable.')
    if sequence_known:
        win_streak = loss_streak = max_win_streak = max_loss_streak = 0
        for row in sorted(rows, key=lambda r: r['date']):
            win_streak = win_streak+1 if row['pnl'] > 0 else 0
            loss_streak = loss_streak+1 if row['pnl'] < 0 else 0
            max_win_streak = max(max_win_streak, win_streak)
            max_loss_streak = max(max_loss_streak, loss_streak)
    elif reliable_dates:
        limitations.append('Tied dates/timestamps: within-day order is unknown, so consecutive-trade streaks are unavailable.')
    m.update(max_drawdown=max_drawdown, max_win_streak=max_win_streak, max_loss_streak=max_loss_streak)
    breakdowns = {}
    for field in ('strategy', 'segment', 'emotion'):
        groups = defaultdict(list)
        for r in rows:
            groups[r.get(field) or 'Unrecorded'].append(r)
        breakdowns[field] = [{'name': name, **metrics(group), 'preliminary': len(group) < 5}
                             for name, group in sorted(groups.items())]
    notes = sum(bool(r.get('has_notes')) for r in rows)
    stops = sum(bool(r.get('has_stop')) for r in rows)
    strategies = sum(bool(r.get('strategy')) for r in rows)
    risks = [r for r in rows if r.get('planned_risk') and r['planned_risk'] > 0]
    breaches = [r for r in risks if -r['pnl'] > r['planned_risk']]
    m['average_r'] = round(sum(r['pnl']/r['planned_risk'] for r in risks)/len(risks), 3) if risks else None
    coverage = {'notes': notes, 'stop_plans': stops, 'strategy_tags': strategies, 'risk_measurable': len(risks), 'total': n}
    strengths, weaknesses = [], []
    confidence = 'preliminary' if n < 30 or source == 'upload' else 'descriptive'

    def finding(target, key, title, evidence, action, check, principle):
        target.append({'id': key, 'title': title, 'evidence': evidence, 'action': action,
                       'success_measure': check, 'principle': principle, 'confidence': confidence})

    if m['pnl'] > 0:
        finding(strengths, 'positive_sample', 'Positive result in this sample',
                f"Total P&L is ₹{m['pnl']:,.2f}; average per record is ₹{m['expectancy']:,.2f}.",
                'Keep the entry/exit process stable while collecting a separate forward sample.',
                'Compare expectancy and profit factor on the next 20 records without increasing size based on this sample alone.', 'probabilities')
    elif m['pnl'] < 0:
        finding(weaknesses, 'negative_sample', 'The current sample loses money',
                f"P&L is ₹{m['pnl']:,.2f}; average per record is ₹{m['expectancy']:,.2f}.",
                'Separate setups and review losses against the written entry/exit plan; test one change in simulation.',
                'Review expectancy and plan adherence on the next 20 comparable records.', 'probabilities')
    if m['payoff_ratio'] is not None:
        if m['payoff_ratio'] >= 1:
            finding(strengths, 'payoff', 'Average winners exceed or match average losers',
                    f"Average win ₹{m['average_win']:,.2f}; average loss ₹{m['average_loss']:,.2f}; payoff {m['payoff_ratio']:.2f}×.",
                    'Review winning exits to identify which repeatable actions helped; avoid assuming every winner was well executed.',
                    'Track payoff alongside win rate in the next review.', 'probabilities')
        elif m['profit_factor'] is not None and (m['profit_factor'] < 1 or m['average_loss'] > 1.5*m['average_win']):
            finding(weaknesses, 'payoff', 'Large average losses leave little room for missed wins',
                    f"Average win ₹{m['average_win']:,.2f}, average loss ₹{m['average_loss']:,.2f}, win rate {m['win_rate']}%, profit factor {m['profit_factor']:.2f}. With these average sizes, break-even needs {m['break_even_win_rate']}% winners among non-flat records.",
                    'Inspect the largest losses and compare planned versus actual exits. Test exit changes before changing live rules.',
                    'Record planned loss, actual loss, and an exit reason on every next trade.', 'risk')
    if m['top_winner_share'] is not None and n >= 5 and (m['top_winner_share'] > 50 or m['pnl'] > 0 > m['pnl_without_best']):
        finding(weaknesses, 'concentration', 'The best winner materially changes the result',
                f"Largest winner supplies {m['top_winner_share']}% of winning P&L; excluding it leaves ₹{m['pnl_without_best']:,.2f}.",
                'Check whether this concentration matches the strategy design; inspect additional independent samples.',
                'Recompute P&L without the best record at the next review; do not automatically remove outlier trades.', 'probabilities')
    if m['losing_pnl'] and m['largest_loss'] / m['losing_pnl'] > 0.5 and n >= 5:
        finding(weaknesses, 'large_loss', 'One large loss dominates the losing side',
                f"Largest loss ₹{m['largest_loss']:,.2f} represents {money(100*m['largest_loss']/m['losing_pnl'])}% of all losing P&L.",
                'Reconstruct this record first: intended size, invalidation point, order execution and exit reason. Identify a testable change only after the cause is documented.',
                'Write one cause-and-evidence review, then track planned versus actual loss on the next 10 positions.', 'risk')
    if source == 'journal':
        if notes == n and strategies == n:
            finding(strengths, 'documentation', 'Every record has a strategy and reflection',
                    f'{notes}/{n} records contain notes and {strategies}/{n} have a meaningful strategy tag.',
                    'Use the notes to score decision quality independently of profit.',
                    'Maintain complete notes and add one specific lesson per session.', 'practice')
        if notes < n or stops < n or strategies < n:
            finding(weaknesses, 'documentation', 'Missing plans prevent a fair process assessment',
                    f'Notes {notes}/{n}; stop plans {stops}/{n}; strategy labels {strategies}/{n}. Missing entries are not proof that no plan existed.',
                    'Before entry, log the setup, invalidation point, intended risk, and exit plan; after exit, record what followed or broke the plan.',
                    'Complete all planning and review fields on the next 10 records.', 'practice')
    if breaches:
        finding(weaknesses, 'risk_overrun', 'Some losses exceeded the recorded initial risk',
                f'{len(breaches)}/{len(risks)} measurable simple positions lost more than their recorded stop-distance risk.',
                'Review gaps, slippage, order execution and plan changes before attributing a cause; the result alone does not prove a stop was ignored.',
                'Explain each overrun and record planned and actual loss on the next 10 comparable positions.', 'risk')
    for kind in ('strategy', 'segment', 'emotion'):
        for group in breakdowns[kind]:
            if group['name'] != 'Unrecorded' and group['count'] >= 5 and group['pnl'] < 0:
                finding(weaknesses, f'{kind}_group_{len(weaknesses)}', f"Review the {group['name']} {kind} group",
                        f"{group['count']} records; P&L ₹{group['pnl']:,.2f}; average ₹{group['expectancy']:,.2f}.",
                        'Compare setup criteria, position sizes and market conditions within this group. Its label is not an explanation of the losses.',
                        'Review the next 10 comparable examples separately before deciding whether a rule change helps.', 'practice')
    if not strengths:
        limitations.append('No repeatable trading strength can be established from the available evidence; winning records alone do not demonstrate discipline.')
    plan = [{'priority': i+1, 'focus': f['title'], 'action': f['action'], 'measure': f['success_measure']}
            for i, f in enumerate(weaknesses[:4])]
    if not plan:
        plan = [{'priority': 1, 'focus': 'Build a forward comparison sample',
                 'action': 'Keep a written setup and review each decision independently of its outcome.',
                 'measure': 'Review the next 20 comparable records for expectancy, payoff, and plan adherence.'}]
    if not risks:
        limitations.append('R-multiples and stop-risk overruns need a valid recorded stop and a simple, fully closed position. Account risk percentage needs capital data.')
    worst = sorted(rows, key=lambda r: r['pnl'])[:min(5, n)]
    return {
        'source': source, 'engine': 'rules', 'metrics': m, 'coverage': coverage,
        'excluded_open': excluded_open, 'strengths': strengths, 'weaknesses': weaknesses,
        'action_plan': plan, 'breakdowns': breakdowns, 'daily': daily, 'equity_curve': curve,
        'review_candidates': [{'id': r['id'], 'symbol': r.get('symbol', 'Unknown'), 'pnl': r['pnl'],
                               'question': 'Was the setup valid, was initial risk recorded, and did the exit follow the plan? Outcome alone is not a process grade.'} for r in worst if r['pnl'] < 0],
        'principles': BOOKS, 'limitations': limitations,
        'summary': f"{n} closed records / report rows: P&L ₹{m['pnl']:,.2f}, win rate {m['win_rate']}%, average ₹{m['expectancy']:,.2f}. Findings describe this sample, not future returns.",
        'methodology': 'Book themes are paraphrased from publisher materials. Metrics, thresholds and exercises are this app’s implementation, not quotations or validated book scoring systems.',
    }
