from datetime import datetime
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.ai_analyzer import analyze_pnl_dataframe
from app.core.pnl import calculate_realized_pnl
from app.routers.trades import ManualLegInput
from app.database.sqlite_db import SessionLocal, TradeModel, LegModel, FillModel, ChargesModel
from app.parsers.zerodha import ZerodhaConsoleParser

CSV = b'''Symbol,Trade Date,Segment,Trade Type,Quantity,Price,Order ID,Trade ID
ABC,2026-05-01 10:00:00,EQ,BUY,10,100,O1,T1
ABC,2026-05-01 14:00:00,EQ,SELL,10,110,O2,T2
'''


def test_reupload_is_idempotent_without_charge_records():
    with TestClient(app) as client:
        first = client.post('/api/ingest/csv', files={'file': ('book.CSV', CSV)})
        second = client.post('/api/ingest/csv', files={'file': ('book.csv', CSV)})
        assert first.status_code == second.status_code == 200
        assert first.json()['trades_ingested'] == 1
        assert second.json()['trades_ingested'] == 0
        with SessionLocal() as db:
            assert db.query(TradeModel).count() == 1
            assert db.query(ChargesModel).count() == 0
            trade = db.query(TradeModel).one()
            assert trade.gross_pnl == trade.net_pnl == 100
            assert trade.total_charges == 0
            assert all(fill.leg_id for fill in db.query(FillModel).all())


def test_overlap_rejected_without_partial_import():
    with TestClient(app) as client:
        client.post('/api/ingest/csv', files={'file': ('book.csv', CSV)})
        extended = CSV + b'ABC,2026-05-02 10:00:00,EQ,BUY,1,105,O3,T3\n'
        res = client.post('/api/ingest/csv', files={'file': ('book.csv', extended)})
        assert res.status_code == 409
        assert client.get('/api/trades').json()['count'] == 1


def test_delete_cascades_and_preserves_other_users():
    with TestClient(app) as client:
        for user in ('single_user', 'other'):
            assert client.post('/api/ingest/csv', params={'user_id': user}, files={'file': ('book.csv', CSV)}).status_code == 200
        assert client.delete('/api/trades').status_code == 200
        with SessionLocal() as db:
            trade = db.query(TradeModel).one()
            assert trade.user_id == 'other'
            for model in (LegModel, FillModel, ChargesModel):
                assert all(row.trade_id == trade.id for row in db.query(model).all())


@pytest.mark.parametrize('change', [{'quantity': -1}, {'quantity': 0}, {'quantity': 1.5}, {'price': -1}, {'side': 'hold'}, {'segment': 'unknown'}, {'instrument': '  '}])
def test_invalid_manual_legs_rejected(change):
    leg = dict(instrument='ABC', segment='Equity', side='buy', price=100, quantity=1)
    leg.update(change)
    with TestClient(app) as client:
        assert client.post('/api/trades', json={'legs': [leg]}).status_code == 422
        assert client.get('/api/trades').json()['count'] == 0


def test_open_position_and_nullable_patch():
    with TestClient(app) as client:
        result = client.post('/api/trades', json={'planned_stop_loss': 90, 'legs': [dict(instrument='ABC', segment='Equity', side='buy', price=100, quantity=10)]})
        assert result.status_code == 200
        assert result.json()['gross_pnl'] == 0
        trade = client.get('/api/trades').json()['trades'][0]
        assert trade['status'] == 'open' and trade['exit_time'] is None
        assert client.patch('/api/trades/' + trade['id'], json={'planned_stop_loss': None}).status_code == 200
        assert client.get('/api/trades').json()['trades'][0]['planned_stop_loss'] is None


def test_fifo_partial_close_and_short_positions():
    legs = [ManualLegInput(instrument='ABC', segment='Equity', side='buy', price=100, quantity=10), ManualLegInput(instrument='ABC', segment='Equity', side='sell', price=120, quantity=4)]
    assert calculate_realized_pnl(legs) == 80
    legs = [ManualLegInput(instrument='ABC', segment='Equity', side='sell', price=120, quantity=10), ManualLegInput(instrument='ABC', segment='Equity', side='buy', price=100, quantity=4)]
    assert calculate_realized_pnl(legs) == 80


@pytest.mark.parametrize('csv', [b'foo,bar\n1,2', CSV.replace(b'BUY', b'INVALID'), CSV.replace(b',10,100,', b',-10,100,'), CSV.replace(b'2026-05-01', b'wrong-date')])
def test_bad_tradebooks_are_rejected(csv):
    with pytest.raises(ValueError):
        ZerodhaConsoleParser().parse_csv(csv)


def test_two_buys_do_not_close_position():
    trade = ZerodhaConsoleParser().parse_csv(CSV.replace(b'SELL', b'BUY'))[0]
    assert trade.status == 'open'
    assert trade.exit_time is None
    assert trade.gross_pnl == 0


def test_analyzer_unsupported_format_returns_validation_error():
    with TestClient(app) as client:
        response = client.post('/api/ai-coach/analyze-csv', files={'file': ('pnl.csv', b'Symbol,Quantity\nABC,10')})
        assert response.status_code == 422


def test_analysis_is_read_only_and_repeatable():
    with TestClient(app) as client:
        for _ in range(2):
            response = client.post('/api/ai-coach/analyze-csv', files={'file': ('pnl.CSV', b'Symbol,PnL\nABC,100')})
            assert response.status_code == 200
            assert response.json()['stats']['net_pnl'] == 100
        assert client.get('/api/trades').json()['count'] == 0


def test_analyzer_total_row_and_formatted_numbers():
    stats = analyze_pnl_dataframe(pd.DataFrame({'Symbol': ['Total', 'ABC', 'XYZ'], 'PnL': ['900', '1,000', '-100']}))
    assert stats['net_pnl'] == 900
    assert stats['total_trades'] == 2
    assert stats['parsed_trades'][0]['net_pnl'] == 1000


def test_analyzer_buy_sell_fallback():
    stats = analyze_pnl_dataframe(pd.DataFrame({'Symbol': ['ABC'], 'Buy Value': [100], 'Sell Value': [120]}))
    assert stats['net_pnl'] == 20


def test_refresh_delete_clears_previous_trades_and_all_children():
    with TestClient(app) as client:
        client.post('/api/ingest/csv', files={'file': ('book.csv', CSV)})
        # Include a historical charge row to verify backward-compatible cleanup.
        with SessionLocal() as db:
            trade = db.query(TradeModel).one()
            db.add(ChargesModel(trade_id=trade.id, brokerage=20, total_charges=20))
            db.commit()
        assert client.delete('/api/trades').status_code == 200
        assert client.get('/api/trades').json() == {'trades': [], 'count': 0}
        with SessionLocal() as db:
            for model in (TradeModel, LegModel, FillModel, ChargesModel):
                assert db.query(model).count() == 0
        assert client.delete('/api/trades').status_code == 200


def test_old_fee_deductions_are_not_exposed_in_trade_list():
    with TestClient(app) as client:
        client.post('/api/ingest/csv', files={'file': ('book.csv', CSV)})
        with SessionLocal() as db:
            trade = db.query(TradeModel).one()
            trade.net_pnl = 80
            trade.total_charges = 20
            db.commit()
        trade = client.get('/api/trades').json()['trades'][0]
        assert trade['gross_pnl'] == trade['net_pnl'] == 100
        assert trade['total_charges'] == 0
