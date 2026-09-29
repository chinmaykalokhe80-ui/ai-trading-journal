from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import uuid

from app.database.sqlite_db import get_db, TradeModel, LegModel
from app.database.firestore import save_trade_to_firestore, delete_all_trades_from_firestore
from app.core.pnl import calculate_realized_pnl
from app.auth import get_user_id

router = APIRouter(prefix="/api", tags=["Trades"])


class ManualLegInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)
    instrument: str = Field(min_length=1)
    segment: Literal["Equity", "Futures", "CE", "PE"]
    side: Literal["buy", "sell"]
    price: float = Field(gt=0)
    quantity: int = Field(gt=0)
    is_delivery: bool = False


class ManualTradeCreate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    strategy_tag: Optional[str] = "Manual Trade"
    emotion_tag: Optional[str] = "Neutral"
    notes: Optional[str] = ""
    planned_stop_loss: Optional[float] = None
    planned_target: Optional[float] = None
    legs: List[ManualLegInput]


class TradeUpdateSchema(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
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
    user_id: str = Depends(get_user_id),
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
                "net_pnl": t.gross_pnl,
                "total_charges": 0.0,
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
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    trade = (
        db.query(TradeModel)
        .filter(TradeModel.id == trade_id, TradeModel.user_id == user_id)
        .first()
    )

    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found.")

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(trade, field, value)

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
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    if not data.legs:
        raise HTTPException(
            status_code=400, detail="Trade must contain at least one leg."
        )

    trade_id = f"trade_{uuid.uuid4().hex[:10]}"
    now = datetime.now()

    pnl = calculate_realized_pnl(data.legs)

    balances = {}
    for leg in data.legs:
        key = (leg.instrument.upper(), leg.segment)
        balances[key] = balances.get(key, 0) + (leg.quantity if leg.side == "buy" else -leg.quantity)
    closed = all(qty == 0 for qty in balances.values())

    trade_row = TradeModel(
        id=trade_id,
        user_id=user_id,
        strategy_id=None,
        strategy_tag=data.strategy_tag,
        entry_time=now,
        exit_time=now if closed else None,
        emotion_tag=data.emotion_tag or "Neutral",
        notes=data.notes or "",
        planned_stop_loss=data.planned_stop_loss,
        planned_target=data.planned_target,
        status="closed" if closed else "open",
        gross_pnl=pnl,
        net_pnl=pnl,
        total_charges=0.0,
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
        "gross_pnl": pnl,
        "net_pnl": pnl,
        "total_charges": 0.0,
    }


@router.delete("/trades")
def clear_all_trades(
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """Deletes all trades for the given user from both SQLite and Firestore."""
    # Delete from SQLite
    for trade in db.query(TradeModel).filter(TradeModel.user_id == user_id).all():
        db.delete(trade)
    db.commit()

    # Sync to Firestore
    delete_all_trades_from_firestore(user_id)

    return {"status": "success", "message": "All trades cleared successfully."}
