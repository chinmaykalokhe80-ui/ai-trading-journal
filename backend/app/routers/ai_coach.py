from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import pandas as pd
import io
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.sqlite_db import get_db, TradeModel, LegModel
from app.core.ai_analyzer import (
    analyze_pnl_dataframe,
    generate_ai_insights_from_csv,
)

router = APIRouter(prefix="/api/ai-coach", tags=["AI Coach"])


@router.post("/analyze-csv")
async def analyze_pnl_csv_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uploads an Equity or F&O PnL CSV or Excel file, computes performance statistics,
    and returns Gemini AI trading coach insights.
    """
    if not (file.filename.endswith(".csv") or file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        raise HTTPException(
            status_code=400, detail="Please upload a valid PnL CSV or Excel export file."
        )

    content = await file.read()

    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode("utf-8-sig")))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Could not parse file: {str(e)}"
        )

    if df.empty:
        raise HTTPException(
            status_code=400, detail="Uploaded CSV file is empty."
        )

    stats = analyze_pnl_dataframe(df)
    parsed_trades = stats.pop("parsed_trades", [])
    insights = generate_ai_insights_from_csv(stats)

    user_id = "single_user"
    now = datetime.now()

    for pt in parsed_trades:
        trade_id = f"trade_{uuid.uuid4().hex[:10]}"
        
        entry_t = now
        if pt.get("date") and pt["date"] != "None":
            try:
                entry_t = pd.to_datetime(pt["date"]).to_pydatetime()
            except Exception:
                pass

        trade = TradeModel(
            id=trade_id,
            user_id=user_id,
            strategy_tag="CSV Upload",
            emotion_tag="Neutral",
            entry_time=entry_t,
            exit_time=entry_t,
            net_pnl=pt["net_pnl"],
            gross_pnl=pt["net_pnl"],
            total_charges=0.0
        )
        db.add(trade)

        leg = LegModel(
            leg_id=f"leg_{uuid.uuid4().hex[:8]}",
            trade_id=trade_id,
            instrument=pt["symbol"],
            segment=pt["segment"],
            side="buy", # defaults to buy for summary view
            price=0.0,
            quantity=pt["quantity"],
            fill_time=entry_t
        )
        db.add(leg)
        
    db.commit()

    return {
        "status": "success",
        "filename": file.filename,
        "stats": stats,
        "insights": insights,
    }
