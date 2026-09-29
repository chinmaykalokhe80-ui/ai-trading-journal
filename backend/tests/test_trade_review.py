from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
import json
import pandas as pd
import pytest
import requests
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.core.trade_review import build_review
from app.core.review_inputs import journal_rows, uploaded_rows
from app.core.llm_review import add_commentary


def rows(values, dates=True):
    return [{'id': f'r{i}', 'pnl': v, 'symbol': 'PRIVATE_SYMBOL', 'strategy': 'PRIVATE_STRATEGY',
             'segment': 'Equity', 'has_notes': True,
             'date': datetime(2026, 1, 1)+timedelta(days=i) if dates else None} for i, v in enumerate(values)]


def test_known_metrics_and_initial_drawdown():
    report = build_review(rows([-100, 200, -50, 0, 300]))
    m = report['metrics']
    assert m['pnl'] == 350 and m['expectancy'] == 70
    assert m['profit_factor'] == m['payoff_ratio'] == 3.333
    assert m['max_drawdown'] == 100
    assert (m['breakeven'], m['wins'], m['losses']) == (1, 2, 2)
    assert m['max_win_streak'] == m['max_loss_streak'] == 1
    assert m['pnl_without_best'] == 50
    assert report['equity_curve'][-1]['pnl'] == 350


@pytest.mark.parametrize('values', [[1, 2], [-1, -2], [0, 0], [100]])
def test_one_sided_samples_have_no_infinite_ratios(values):
    report = build_review(rows(values))
    json.dumps(report, allow_nan=False)
    assert report['metrics']['payoff_ratio'] is None
    if all(v >= 0 for v in values):
        assert report['metrics']['profit_factor'] is None
    else:
        assert report['metrics']['profit_factor'] == 0


def test_unknown_and_tied_dates():
    report = build_review(rows([100, -200], dates=False))
    assert report['metrics']['max_drawdown'] is None
    assert report['metrics']['max_loss_streak'] is None
    assert report['daily'] == report['equity_curve'] == []
    data = rows([100, -200]); data[1]['date'] = data[0]['date']
    report = build_review(data)
    assert report['metrics']['max_drawdown'] == 100
    assert report['metrics']['max_loss_streak'] is None


def test_losses_do_not_diagnose_revenge_or_invent_strengths():
    report = build_review(rows([-100, -200, -300], dates=False), source='upload')
    assert report['strengths'] == []
    assert any(f['id'] == 'negative_sample' for f in report['weaknesses'])
    assert all('revenge' not in f['evidence'].lower() for f in report['weaknesses'])
    assert report['action_plan'][0]['measure']


def test_journal_legacy_dates_and_open_records():
    leg = SimpleNamespace(instrument='ABC', segment='Equity', price=0, quantity=1, side='buy', fill_time=datetime(2026,1,1))
    trade = SimpleNamespace(id='legacy', status='closed', gross_pnl=100, entry_time=leg.fill_time, exit_time=leg.fill_time,
                            notes=None, strategy_tag='CSV Upload', emotion_tag='Neutral', planned_stop_loss=None, legs=[leg])
    data, excluded = journal_rows([trade, SimpleNamespace(status='open')])
    assert excluded == 1
    assert data[0]['date'] is None and data[0]['strategy'] is None
    report = build_review(data)
    assert report['coverage']['notes'] == report['coverage']['stop_plans'] == 0
    assert report['metrics']['max_drawdown'] is None


def test_risk_only_simple_complete_positions():
    first = SimpleNamespace(instrument='ABC', segment='Equity', price=100, quantity=10, side='buy', fill_time=datetime(2026,1,1))
    last = SimpleNamespace(instrument='ABC', segment='Equity', price=80, quantity=10, side='sell', fill_time=datetime(2026,1,2))
    trade = SimpleNamespace(id='t', status='closed', gross_pnl=-200, entry_time=first.fill_time, exit_time=last.fill_time,
                            notes='review', strategy_tag='Breakout', emotion_tag='Confident', planned_stop_loss=90, legs=[first, last])
    data, _ = journal_rows([trade]); report = build_review(data)
    assert report['metrics']['average_r'] == -2
    assert any(f['id'] == 'risk_overrun' for f in report['weaknesses'])
    trade.legs.append(first)
    data, _ = journal_rows([trade]); assert data[0]['planned_risk'] is None


def test_default_never_calls_network_even_with_key(monkeypatch):
    monkeypatch.setattr(settings, 'GEMINI_API_KEY', 'test-key')
    post = Mock(side_effect=AssertionError('Unexpected network'))
    monkeypatch.setattr('app.core.llm_review.requests.post', post)
    result = add_commentary(build_review(rows([100, -50])))
    assert result['llm']['status'] == 'not_requested'
    post.assert_not_called()


@pytest.mark.parametrize('provider,key', [('gemini','GEMINI_API_KEY'), ('groq','GROQ_API_KEY'), ('openrouter','OPENROUTER_API_KEY')])
def test_provider_receives_only_aggregates(provider, key, monkeypatch):
    monkeypatch.setattr(settings, key, 'test-secret')
    result = {'summary': 'Review the sample.', 'review_questions': ['Was the plan followed?'], 'practice_exercise': 'Log an exit reason.', 'evidence_ids': ['positive_sample']}
    response = Mock(); content = json.dumps(result)
    response.json.return_value = {'candidates': [{'content': {'parts': [{'text': content}]}}]} if provider == 'gemini' else {'choices': [{'message': {'content': content}}]}
    post = Mock(return_value=response); monkeypatch.setattr('app.core.llm_review.requests.post', post)
    report = build_review(rows([100, -50])); report['private_notes'] = 'DO_NOT_SEND'
    add_commentary(report, provider)
    assert report['llm']['status'] == 'success'
    body = json.dumps(post.call_args.kwargs['json'])
    for secret in ('PRIVATE_SYMBOL', 'PRIVATE_STRATEGY', 'DO_NOT_SEND', 'test-secret'):
        assert secret not in body
    assert report['metrics']['pnl'] == 50


@pytest.mark.parametrize('failure', ['timeout', '429', 'malformed', 'invented_evidence'])
def test_provider_failure_keeps_local_report(failure, monkeypatch):
    monkeypatch.setattr(settings, 'GROQ_API_KEY', 'test-secret')
    response = Mock()
    if failure == '429': response.raise_for_status.side_effect = requests.HTTPError('429')
    response.json.return_value = {'choices': [{'message': {'content': 'not json' if failure == 'malformed' else json.dumps({'summary':'s','review_questions':['q'],'practice_exercise':'p','evidence_ids':['fake']})}}]}
    monkeypatch.setattr('app.core.llm_review.requests.post', Mock(side_effect=requests.Timeout if failure == 'timeout' else None, return_value=response))
    report = add_commentary(build_review(rows([100, -50])), 'groq')
    assert report['llm']['status'] == 'unavailable'
    assert report['metrics']['pnl'] == 50 and report['strengths']


def test_openrouter_rejects_paid_models(monkeypatch):
    monkeypatch.setattr(settings, 'OPENROUTER_API_KEY', 'key')
    monkeypatch.setattr(settings, 'OPENROUTER_MODEL', 'paid/model')
    post = Mock(); monkeypatch.setattr('app.core.llm_review.requests.post', post)
    assert add_commentary(build_review(rows([1])), 'openrouter')['llm']['status'] == 'unavailable'
    post.assert_not_called()


def test_journal_endpoint_readonly_isolated_and_validated():
    with TestClient(app) as client:
        assert client.post('/api/ai-coach/analyze-journal', json={}).status_code == 422
        payload = {'legs': [{'instrument':'ABC','segment':'Equity','side':side,'price':price,'quantity':10} for side,price in [('buy',100),('sell',110)]]}
        client.post('/api/trades', json=payload)
        for _ in range(2):
            response = client.post('/api/ai-coach/analyze-journal', json={})
            assert response.status_code == 200
            assert response.json()['report']['metrics']['pnl'] == 100
            assert response.json()['report']['llm']['status'] == 'not_requested'
        assert client.get('/api/trades').json()['count'] == 1
        assert client.post('/api/ai-coach/analyze-journal', json={'provider':'unknown'}).status_code == 422
        assert client.post('/api/ai-coach/analyze-journal?user_id=other', json={}).status_code == 422


def test_provider_discovery_hides_keys(monkeypatch):
    monkeypatch.setattr(settings, 'GROQ_API_KEY', 'DO_NOT_DISCLOSE')
    with TestClient(app) as client:
        response = client.get('/api/ai-coach/providers')
        assert response.status_code == 200 and 'DO_NOT_DISCLOSE' not in response.text


def test_upload_preserves_dates_strategies_and_ampersand_pnl():
    data, _ = uploaded_rows(pd.DataFrame({'Symbol': ['ABC','XYZ'], 'P&L': [100,-20], 'Date': ['2026-01-02','2026-01-03'], 'Strategy': ['Breakout','Breakout']}))
    report = build_review(data, source='upload')
    assert report['metrics']['max_drawdown'] == 20
    assert report['breakdowns']['strategy'][0]['name'] == 'Breakout'


def test_high_win_rate_still_flags_oversized_average_losses():
    report = build_review(rows([100, 100, 100, -280]))
    assert report['metrics']['pnl'] > 0
    assert report['metrics']['profit_factor'] > 1
    assert any(f['id'] == 'payoff' for f in report['weaknesses'])
    assert report['metrics']['break_even_win_rate'] == 73.68


def test_winner_sensitivity_and_large_loss_concentration():
    report = build_review(rows([1000, 100, 100, -900, -10]))
    ids = {f['id'] for f in report['weaknesses']}
    assert 'concentration' in ids and 'large_loss' in ids
    assert report['metrics']['pnl_without_best'] == -710


def test_report_formats_numbers_and_rejects_bad_buy_sell_values():
    data, _ = uploaded_rows(pd.DataFrame({'Symbol':['ABC'], 'Buy Value':['1,000'], 'Sell Value':['1,200']}))
    assert data[0]['pnl'] == 200
    data, _ = uploaded_rows(pd.DataFrame({'Symbol':['ABC'], 'PnL':['(1,200)']}))
    assert data[0]['pnl'] == -1200
    with pytest.raises(ValueError):
        uploaded_rows(pd.DataFrame({'Symbol':['ABC'], 'Buy Value':['invalid'], 'Sell Value':[100]}))
