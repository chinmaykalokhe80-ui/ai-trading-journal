from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool
import pandas as pd
import io
from app.database.sqlite_db import get_db, TradeModel
from app.core.ai_analyzer import legacy_insights
from app.core.trade_review import build_review
from app.core.review_inputs import uploaded_rows, journal_rows
from app.core.llm_review import Provider, providers, add_commentary
from app.core.broker_pnl_workbook import parse_broker_pnl_workbook

router = APIRouter(prefix='/api/ai-coach', tags=['AI Coach'])


class ReviewRequest(BaseModel):
    provider: Provider = 'rules'


@router.get('/providers')
def list_providers():
    return {'providers': providers()}


@router.post('/analyze-journal')
def analyze_journal(data: ReviewRequest, user_id: str = 'single_user', db: Session = Depends(get_db)):
    trades = db.query(TradeModel).options(selectinload(TradeModel.legs)).filter(TradeModel.user_id == user_id).all()
    rows, excluded = journal_rows(trades)
    try:
        report = build_review(rows, excluded_open=excluded)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    add_commentary(report, data.provider)
    return {'status': 'success', 'report': report, 'insights': legacy_insights(report)}


@router.post('/analyze-csv')
async def analyze_pnl_csv_endpoint(file: UploadFile = File(...), provider: Provider = 'rules'):
    """Read-only report analysis; optional LLM sees only computed aggregates."""
    filename = (file.filename or '').lower()
    if not filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail='Please upload a PnL CSV or Excel report.')
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='Please upload a file smaller than 10 MB.')

    def analyze():
        try:
            statement = None
            if filename.endswith('.xlsx'):
                parsed = parse_broker_pnl_workbook(content)
                if parsed is not None:
                    df, statement = parsed
                else:
                    df = pd.read_excel(io.BytesIO(content))
            elif filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(content.decode('utf-8-sig')))
            else:
                df = pd.read_excel(io.BytesIO(content))
            if df.empty:
                raise ValueError('The report contains no trade rows.')
            rows, stats = uploaded_rows(df)
            report = build_review(rows, source='upload')
            if statement is not None:
                report['statement'] = statement
                report['summary'] = report['summary'].replace(
                    f'{len(rows)} closed records / report rows', f'{len(rows)} contract rows')
                report['limitations'].append(
                    'This broker statement aggregates executions by contract. Contract rows are not individual trades, and the period range does not provide trade dates or execution order.')
                report['limitations'].append(
                    'Charges and adjustments are broker-reported separately; they are not deducted from the realized P&L used in this review.')
        except (ValueError, KeyError, TypeError, OverflowError, ImportError) as exc:
            raise HTTPException(status_code=422, detail=f'Could not analyze report: {exc}') from exc
        add_commentary(report, provider)
        return {'status': 'success', 'filename': file.filename, 'stats': stats, 'report': report,
                'insights': legacy_insights(report)}

    return await run_in_threadpool(analyze)
