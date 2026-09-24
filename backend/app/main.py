from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database.sqlite_db import init_db
from app.routers import ingest, trades, ai_coach


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_db()
    yield
    # Shutdown logic


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Backend API for Indian Equity & F&O Trading Journal with automated charge calculation, CSV ingestion, and analytics.",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(trades.router)
app.include_router(ai_coach.router)


@app.get("/")
def root():
    return {
        "message": "Indian Equity & F&O Trading Journal API is running",
        "docs": "/docs",
    }
