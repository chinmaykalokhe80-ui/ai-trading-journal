import pytest
from app.parsers.zerodha import ZerodhaConsoleParser


def test_zerodha_parser_sample_csv():
    sample_csv = """Symbol,Trade Date,Exchange,Segment,Trade Type,Quantity,Price,Order ID,Trade ID
RELIANCE,2026-05-01 10:00:00,NSE,EQ,BUY,100,2500,ORD1001,TRD1
RELIANCE,2026-05-01 14:30:00,NSE,EQ,SELL,100,2600,ORD1002,TRD2
NIFTY 24000 CE,2026-05-02 09:15:00,NFO,FO,SELL,50,120,ORD2001,TRD3
NIFTY 24000 CE,2026-05-02 11:00:00,NFO,FO,BUY,50,40,ORD2002,TRD4
"""

    parser = ZerodhaConsoleParser()
    trades = parser.parse_csv(sample_csv.encode("utf-8"))

    assert len(trades) == 2

    # Check RELIANCE trade
    reliance_trade = next(t for t in trades if t.instrument == "RELIANCE")
    assert reliance_trade.gross_pnl == 10000.0
    assert len(reliance_trade.legs) == 2

    # Check NIFTY Option trade
    nifty_trade = next(t for t in trades if "NIFTY" in t.instrument)
    assert nifty_trade.gross_pnl == 4000.0
    assert nifty_trade.segment in ("CE", "PE")
    assert len(nifty_trade.legs) == 2
