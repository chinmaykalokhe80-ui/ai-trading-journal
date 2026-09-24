from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.database.sqlite_db import get_db, TradeModel, LegModel, ChargesModel
from app.database.firestore import save_trade_to_firestore, delete_all_trades_from_firestore
from app.core.charges_engine import (
    calculate_trade_charges,
    TradeLegInput,
    DEFAULT_CHARGES_CONFIG,
)

router = APIRouter(prefix="/api", tags=["Trades"])


class ManualLegInput(BaseModel):
    instrument: str
    segment: str  # "Equity", "Futures", "CE", "PE"
    side: str  # "buy", "sell"
    price: float
    quantity: int
    is_delivery: bool = False


class ManualTradeCreate(BaseModel):
    strategy_tag: Optional[str] = "Manual Trade"
    emotion_tag: Optional[str] = "Neutral"
    notes: Optional[str] = ""
    planned_stop_loss: Optional[float] = None
    planned_target: Optional[float] = None
    legs: List[ManualLegInput]


class TradeUpdateSchema(BaseModel):
    strategy_id: Optional[str] = None
    strategy_tag: Optional[str] = None
    emotion_tag: Optional[str] = None
    notes: Optional[str] = None
    planned_stop_loss: Optional[float] = None
    planned_target: Optional[float] = None


@router.get("/trades")
def list_trades(
    segment: Optional[str] = None,
    emotion_tag: Optional[str] = None,
    strategy_tag: Optional[str] = None,
    user_id: str = "single_user",
    db: Session = Depends(get_db),
):
    query = db.query(TradeModel).filter(TradeModel.user_id == user_id)

    if emotion_tag:
        query = query.filter(TradeModel.emotion_tag == emotion_tag)
    if strategy_tag:
        query = query.filter(TradeModel.strategy_tag == strategy_tag)

    trades = query.order_by(TradeModel.entry_time.desc()).all()

    result = []
    for t in trades:
        legs = db.query(LegModel).filter(LegModel.trade_id == t.id).all()
        # Filter segment if requested
        if segment and not any(
            l.segment.lower() == segment.lower() for l in legs
        ):
            continue

        result.append(
            {
                "id": t.id,
                "strategy_id": t.strategy_id,
                "strategy_tag": t.strategy_tag,
                "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "emotion_tag": t.emotion_tag,
                "notes": t.notes,
                "planned_stop_loss": t.planned_stop_loss,
                "planned_target": t.planned_target,
                "screenshot_url": t.screenshot_url,
                "status": t.status,
                "gross_pnl": t.gross_pnl,
                "net_pnl": t.net_pnl,
                "total_charges": t.total_charges,
                "legs": [
                    {
                        "leg_id": l.leg_id,
                        "instrument": l.instrument,
                        "segment": l.segment,
                        "side": l.side,
                        "price": l.price,
                        "quantity": l.quantity,
                        "lot_size": l.lot_size,
                        "order_id": l.order_id,
                        "fill_time": (
                            l.fill_time.isoformat() if l.fill_time else None
                        ),
                    }
                    for l in legs
                ],
            }
        )

    return {"trades": result, "count": len(result)}


@router.patch("/trades/{trade_id}")
def update_trade(
    trade_id: str,
    update_data: TradeUpdateSchema,
    user_id: str = "single_user",
    db: Session = Depends(get_db),
):
    trade = (
        db.query(TradeModel)
        .filter(TradeModel.id == trade_id, TradeModel.user_id == user_id)
        .first()
    )

    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found.")

    if update_data.strategy_id is not None:
        trade.strategy_id = update_data.strategy_id
    if update_data.strategy_tag is not None:
        trade.strategy_tag = update_data.strategy_tag
    if update_data.emotion_tag is not None:
        trade.emotion_tag = update_data.emotion_tag
    if update_data.notes is not None:
        trade.notes = update_data.notes
    if update_data.planned_stop_loss is not None:
        trade.planned_stop_loss = update_data.planned_stop_loss
    if update_data.planned_target is not None:
        trade.planned_target = update_data.planned_target

    db.commit()
    db.refresh(trade)

    # Sync update to Firestore
    save_trade_to_firestore(
        {
            "id": trade.id,
            "user_id": trade.user_id,
            "strategy_id": trade.strategy_id,
            "strategy_tag": trade.strategy_tag,
            "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            "emotion_tag": trade.emotion_tag,
            "notes": trade.notes,
            "planned_stop_loss": trade.planned_stop_loss,
            "planned_target": trade.planned_target,
            "status": trade.status,
            "gross_pnl": trade.gross_pnl,
            "net_pnl": trade.net_pnl,
            "total_charges": trade.total_charges,
        }
    )

    return {"status": "success", "trade_id": trade.id}


@router.post("/trades")
def create_manual_trade(
    data: ManualTradeCreate,
    user_id: str = "single_user",
    db: Session = Depends(get_db),
):
    if not data.legs:
        raise HTTPException(
            status_code=400, detail="Trade must contain at least one leg."
        )

    trade_id = f"trade_{uuid.uuid4().hex[:10]}"
    now = datetime.now()

    engine_legs = [
        TradeLegInput(
            leg_id=f"leg_{idx}",
            instrument=l.instrument,
            segment=l.segment,
            side=l.side,
            price=l.price,
            quantity=l.quantity,
            is_delivery=l.is_delivery,
        )
        for idx, l in enumerate(data.legs)
    ]

    charges_res = calculate_trade_charges(engine_legs, trade_date=now)

    trade_row = TradeModel(
        id=trade_id,
        user_id=user_id,
        strategy_id=None,
        strategy_tag=data.strategy_tag,
        entry_time=now,
        exit_time=now,
        emotion_tag=data.emotion_tag or "Neutral",
        notes=data.notes or "",
        planned_stop_loss=data.planned_stop_loss,
        planned_target=data.planned_target,
        status="closed",
        gross_pnl=charges_res.gross_pnl,
        net_pnl=charges_res.net_pnl,
        total_charges=charges_res.total_charges,
    )
    db.add(trade_row)

    for idx, l in enumerate(data.legs):
        leg_row = LegModel(
            leg_id=f"leg_{uuid.uuid4().hex[:8]}",
            trade_id=trade_id,
            instrument=l.instrument,
            segment=l.segment,
            side=l.side,
            price=l.price,
            quantity=l.quantity,
            lot_size=25 if l.segment.upper() in ("CE", "PE", "FUTURES") else 1,
            order_id=f"man_ord_{idx}",
            fill_time=now,
            is_delivery=l.is_delivery,
        )
        db.add(leg_row)

    db.commit()

    return {
        "status": "success",
        "trade_id": trade_id,
        "gross_pnl": charges_res.gross_pnl,
        "net_pnl": charges_res.net_pnl,
        "total_charges": charges_res.total_charges,
    }


@router.get("/charges-config")
def get_charges_config():
    """Returns the current charges_config rate structure and tax disclaimer."""
    return {
        "configs": DEFAULT_CHARGES_CONFIG,
        "disclaimer": (
            "IMPORTANT NOTICE: The charges and tax rates provided here reflect standard Indian Equity & F&O "
            "exchange fees, STT (including Budget 2026-27 updates), GST, SEBI fees, and Stamp Duty. "
            "Please double-check all rates against the official Zerodha/NSE charges page before relying on "
            "computed Net PnL figures for tax filing."
        ),
    }


@router.delete("/trades")
def clear_all_trades(
    user_id: str = "single_user",
    db: Session = Depends(get_db),
):
    """Deletes all trades for the given user from both SQLite and Firestore."""
    # Delete from SQLite
    db.query(TradeModel).filter(TradeModel.user_id == user_id).delete(synchronize_session=False)
    db.commit()

    # Sync to Firestore
    delete_all_trades_from_firestore(user_id)

    return {"status": "success", "message": "All trades cleared successfully."}
