import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.sqlite_db import init_db


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


def test_ai_coach_analyze_csv_endpoint():
    with TestClient(app) as client:
        csv_content = """Symbol,Buy Value,Sell Value,PnL,Charges
NIFTY 24000 CE,10000,15000,5000,250
BANKNIFTY 50000 PE,8000,4000,-4000,200
RELIANCE,25000,27000,2000,100
"""
        files = {"file": ("pnl_report.csv", csv_content, "text/csv")}
        response = client.post("/api/ai-coach/analyze-csv", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "stats" in data
        assert "insights" in data
        assert data["stats"]["total_trades"] == 3
        assert "executive_summary" in data["insights"]
        assert len(data["insights"]["actionable_recommendations"]) >= 1
