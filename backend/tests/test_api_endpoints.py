import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.sqlite_db import init_db


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


def test_root_endpoint():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Trading Journal API" in response.json()["message"]


def test_charges_config_removed():
    with TestClient(app) as client:
        assert client.get("/api/charges-config").status_code == 404


def test_manual_trade_creation_and_list():
    with TestClient(app) as client:
        payload = {
            "strategy_tag": "Breakout Strategy",
            "emotion_tag": "Confident",
            "notes": "Testing manual entry",
            "planned_stop_loss": 2450.0,
            "planned_target": 2650.0,
            "legs": [
                {
                    "instrument": "RELIANCE",
                    "segment": "Equity",
                    "side": "buy",
                    "price": 2500.0,
                    "quantity": 100,
                    "is_delivery": True,
                },
                {
                    "instrument": "RELIANCE",
                    "segment": "Equity",
                    "side": "sell",
                    "price": 2600.0,
                    "quantity": 100,
                    "is_delivery": True,
                },
            ],
        }

        create_res = client.post("/api/trades", json=payload)
        assert create_res.status_code == 200
        res_data = create_res.json()
        assert res_data["status"] == "success"
        assert res_data["gross_pnl"] == res_data["net_pnl"] == 10000.0
        assert res_data["total_charges"] == 0
        trade_id = res_data["trade_id"]

        # Test List Trades
        list_res = client.get("/api/trades")
        assert list_res.status_code == 200
        trades_list = list_res.json()["trades"]
        assert len(trades_list) >= 1

        # Test Patch Trade
        patch_res = client.patch(
            f"/api/trades/{trade_id}",
            json={"emotion_tag": "Disciplined", "notes": "Updated note test"},
        )
        assert patch_res.status_code == 200


def test_csv_ingest_endpoint():
    with TestClient(app) as client:
        csv_content = """Symbol,Trade Date,Exchange,Segment,Trade Type,Quantity,Price,Order ID,Trade ID
TATAMOTORS,2026-05-10 10:00:00,NSE,EQ,BUY,50,900,ORD9001,TRD901
TATAMOTORS,2026-05-10 15:00:00,NSE,EQ,SELL,50,950,ORD9002,TRD902
"""
        files = {"file": ("tradebook.csv", csv_content, "text/csv")}
        response = client.post("/api/ingest/csv", files=files)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["trades_ingested"] == 1
