from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid

from app.database.sqlite_db import (
    get_db,
    TradeModel,
    LegModel,
    FillModel,
    ChargesModel,
)
from app.database.firestore import save_trade_to_firestore
from app.parsers.zerodha import ZerodhaConsoleParser

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])


@router.post("/csv")
async def ingest_csv(
    file: UploadFile = File(...),
    user_id: str = "single_user",
    db: Session = Depends(get_db),
):
    """Uploads and ingests Zerodha Console Tradebook CSV, parses trades/legs/fills,

    calculates Indian charges/taxes, saves to Firestore and mirrors into local SQLite cache.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400, detail="Only CSV files are supported."
        )

    content = await file.read()
    parser = ZerodhaConsoleParser()

    try:
        parsed_trades = parser.parse_csv(content, user_id=user_id)
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Failed to parse CSV file: {str(e)}"
        )

    ingested_count = 0

    for pt in parsed_trades:
        # 1. Save to SQLite database
        existing_trade = (
            db.query(TradeModel).filter(TradeModel.id == pt.trade_id).first()
        )
        if not existing_trade:
            trade_row = TradeModel(
                id=pt.trade_id,
                user_id=user_id,
                strategy_id=pt.strategy_id,
                strategy_tag=pt.strategy_tag,
                entry_time=pt.entry_time,
                exit_time=pt.exit_time,
                emotion_tag="Neutral",
                notes="",
                status=pt.status,
                gross_pnl=pt.gross_pnl,
                net_pnl=pt.net_pnl,
                total_charges=pt.total_charges,
            )
            db.add(trade_row)

            for leg in pt.legs:
                leg_row = LegModel(
                    leg_id=leg.leg_id,
                    trade_id=pt.trade_id,
                    instrument=leg.instrument,
                    segment=leg.segment,
                    side=leg.side,
                    price=leg.price,
                    quantity=leg.quantity,
                    lot_size=leg.lot_size,
                    order_id=leg.order_id,
                    fill_time=leg.fill_time,
                    is_delivery=leg.is_delivery,
                )
                db.add(leg_row)

            for fill in pt.fills:
                fill_row = FillModel(
                    fill_id=fill.fill_id,
                    trade_id=pt.trade_id,
                    leg_id=getattr(fill, "leg_id", None),
                    quantity=fill.quantity,
                    price=fill.price,
                    fill_time=fill.fill_time,
                )
                db.add(fill_row)

            charges_row = ChargesModel(
                trade_id=pt.trade_id,
                brokerage=round(pt.total_charges * 0.2, 2),  # Estimated split
                stt=round(pt.total_charges * 0.5, 2),
                exchange_txn_charge=round(pt.total_charges * 0.15, 2),
                gst=round(pt.total_charges * 0.1, 2),
                sebi_charges=round(pt.total_charges * 0.02, 2),
                stamp_duty=round(pt.total_charges * 0.03, 2),
                dp_charges=0.0,
                total_charges=pt.total_charges,
            )
            db.add(charges_row)
            ingested_count += 1

            # 2. Mirror to Firestore ledger
            trade_dict = {
                "id": pt.trade_id,
                "user_id": user_id,
                "strategy_id": pt.strategy_id,
                "strategy_tag": pt.strategy_tag,
                "entry_time": pt.entry_time.isoformat() if pt.entry_time else None,
                "exit_time": pt.exit_time.isoformat() if pt.exit_time else None,
                "emotion_tag": "Neutral",
                "notes": "",
                "status": pt.status,
                "gross_pnl": pt.gross_pnl,
                "net_pnl": pt.net_pnl,
                "total_charges": pt.total_charges,
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
                        "fill_time": l.fill_time.isoformat() if l.fill_time else None,
                    }
                    for l in pt.legs
                ],
                "fills": [
                    {
                        "fill_id": f.fill_id,
                        "quantity": f.quantity,
                        "price": f.price,
                        "time": f.fill_time.isoformat() if f.fill_time else None,
                    }
                    for f in pt.fills
                ],
            }
            save_trade_to_firestore(trade_dict)

    db.commit()

    return {
        "status": "success",
        "message": f"Successfully ingested {ingested_count} trades.",
        "trades_ingested": ingested_count,
    }
