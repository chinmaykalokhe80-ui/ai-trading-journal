import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("kite_stub")


class KiteConnectClient:
    """Placeholder Kite Connect API Client Stub.

    IMPORTANT SECRETS HANDLING NOTE:
    API key and secret MUST NEVER be stored in frontend code or committed into git version control.
    They are loaded strictly from environment variables (KITE_API_KEY, KITE_API_SECRET).
    In production environments (AWS KMS, GCP Secret Manager, HashiCorp Vault), read from
    a secure secrets manager instead of a plaintext .env file.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("KITE_API_KEY", "")
        self.api_secret = api_secret or os.getenv("KITE_API_SECRET", "")
        self.access_token = access_token or os.getenv("KITE_ACCESS_TOKEN", "")

        if not self.api_key or not self.api_secret:
            logger.info(
                "KiteConnectClient initialized in stub mode (KITE_API_KEY / KITE_API_SECRET not set)."
            )

    def generate_login_url(self) -> str:
        return f"https://kite.zerodha.com/connect/login?v=3&api_key={self.api_key}"

    def generate_session(self, request_token: str) -> Dict[str, Any]:
        """Stub method to exchange request_token for an access_token."""
        logger.info(
            f"Generating session for request_token: {request_token[:6]}..."
        )
        fake_token = f"stub_token_{request_token}"
        self.access_token = fake_token
        return {
            "access_token": fake_token,
            "user_type": "individual",
            "email": "trader@example.com",
            "user_name": "Pro Trader",
        }

    def fetch_positions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Stub method to fetch current open/day positions."""
        return {
            "net": [
                {
                    "tradingsymbol": "NIFTY24MAY24000CE",
                    "exchange": "NFO",
                    "quantity": 0,
                    "buy_quantity": 50,
                    "sell_quantity": 50,
                    "pnl": 4000.0,
                }
            ],
            "day": [],
        }

    def fetch_historical_trades(
        self, from_date: str, to_date: str
    ) -> List[Dict[str, Any]]:
        """Stub method to fetch executed historical trades for a date range."""
        return [
            {
                "trade_id": "stub_trd_001",
                "order_id": "stub_ord_001",
                "tradingsymbol": "RELIANCE",
                "exchange": "NSE",
                "transaction_type": "BUY",
                "quantity": 100,
                "average_price": 2500.0,
                "order_timestamp": f"{from_date} 10:00:00",
            },
            {
                "trade_id": "stub_trd_002",
                "order_id": "stub_ord_002",
                "tradingsymbol": "RELIANCE",
                "exchange": "NSE",
                "transaction_type": "SELL",
                "quantity": 100,
                "average_price": 2600.0,
                "order_timestamp": f"{from_date} 14:30:00",
            },
        ]
