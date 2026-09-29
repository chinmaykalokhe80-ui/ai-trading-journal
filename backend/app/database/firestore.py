import os
import logging
from typing import Dict, Any, List, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from app.config import settings

logger = logging.getLogger("firestore")

db_client = None

try:
    cred_path = settings.FIREBASE_SERVICE_ACCOUNT_PATH
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db_client = firestore.client()
        logger.info("Firebase Admin initialized with service account.")
    elif not firebase_admin._apps:
        # Initialize default app if env variable has project id or emulator
        if os.getenv("FIRESTORE_EMULATOR_HOST"):
            firebase_admin.initialize_app()
            db_client = firestore.client()
            logger.info("Firebase Admin initialized using Firestore Emulator.")
        else:
            logger.warning(
                "No Firebase credentials found. Operating in local SQLite-only fallback mode until FIREBASE_SERVICE_ACCOUNT_PATH is set."
            )
except Exception as e:
    logger.warning(f"Firestore initialization fallback: {e}")
    db_client = None


def save_trade_to_firestore(trade_dict: Dict[str, Any]) -> bool:
    """Saves parent trade document and legs/fills subcollections to Firestore if configured."""
    if db_client is None:
        return False

    try:
        trade_id = trade_dict["id"]
        doc_ref = db_client.collection("trades").document(trade_id)

        parent_data = {
            "id": trade_id,
            "userId": trade_dict.get("user_id", "single_user"),
            "strategy_id": trade_dict.get("strategy_id"),
            "strategy_tag": trade_dict.get("strategy_tag"),
            "entry_time": trade_dict.get("entry_time"),
            "exit_time": trade_dict.get("exit_time"),
            "emotion_tag": trade_dict.get("emotion_tag", "Neutral"),
            "notes": trade_dict.get("notes", ""),
            "planned_stop_loss": trade_dict.get("planned_stop_loss"),
            "planned_target": trade_dict.get("planned_target"),
            "screenshot_url": trade_dict.get("screenshot_url"),
            "status": trade_dict.get("status", "closed"),
            "gross_pnl": trade_dict.get("gross_pnl", 0.0),
            "net_pnl": trade_dict.get("net_pnl", 0.0),
            "total_charges": trade_dict.get("total_charges", 0.0),
        }
        doc_ref.set(parent_data, merge=True)

        for leg in trade_dict.get("legs", []):
            doc_ref.collection("legs").document(leg["leg_id"]).set(
                leg, merge=True
            )

        for fill in trade_dict.get("fills", []):
            doc_ref.collection("fills").document(fill["fill_id"]).set(
                fill, merge=True
            )

        return True
    except Exception as e:
        logger.error(f"Error saving trade to Firestore: {e}")
        return False


def get_firestore_security_rules_template() -> str:
    """Returns standard Firestore security rules template for User data isolation."""
    return """rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /charges_config/{configId} {
      allow read: if request.auth != null;
      allow write: if false; // Admin/Seeded only
    }
    match /trades/{tradeId} {
      allow read, write, delete: if request.auth != null && request.auth.uid == resource.data.userId;
      
      match /legs/{legId} {
        allow read, write: if request.auth != null && get(/databases/$(database)/documents/trades/$(tradeId)).data.userId == request.auth.uid;
      }
      match /fills/{fillId} {
        allow read, write: if request.auth != null && get(/databases/$(database)/documents/trades/$(tradeId)).data.userId == request.auth.uid;
      }
    }
  }
}"""

def delete_all_trades_from_firestore(user_id: str = "single_user") -> bool:
    """Deletes all trades for a given user from Firestore."""
    if db_client is None:
        return False

    try:
        trades_ref = db_client.collection("trades").where("userId", "==", user_id).stream()
        for trade in trades_ref:
            trade_id = trade.id
            doc_ref = db_client.collection("trades").document(trade_id)
            
            # Delete legs
            legs_ref = doc_ref.collection("legs").stream()
            for leg in legs_ref:
                leg.reference.delete()
                
            # Delete fills
            fills_ref = doc_ref.collection("fills").stream()
            for fill in fills_ref:
                fill.reference.delete()
                
            # Delete parent trade
            doc_ref.delete()
        return True
    except Exception as e:
        logger.error(f"Error deleting trades from Firestore: {e}")
        return False
