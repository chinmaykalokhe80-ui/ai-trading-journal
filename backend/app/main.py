from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.auth import get_user_id, validate_production_config, production_mode
from app.database.sqlite_db import init_db
from app.routers import ingest, trades, ai_coach


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    validate_production_config()
    init_db()
    yield
    # Shutdown logic


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Backend API for Indian Equity & F&O Trading Journal with CSV ingestion, realized P&L, and analytics.",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if production_mode() else ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, dependencies=[Depends(get_user_id)])
app.include_router(trades.router, dependencies=[Depends(get_user_id)])
app.include_router(ai_coach.router, dependencies=[Depends(get_user_id)])


@app.get("/")
def root():
    return {
        "message": "Indian Equity & F&O Trading Journal API is running",
        "docs": "/docs",
    }
