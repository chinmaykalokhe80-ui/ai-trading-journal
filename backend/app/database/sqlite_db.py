import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from app.config import settings

DB_PATH = settings.SQLITE_DB_PATH
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TradeModel(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, default="single_user")
    strategy_id = Column(String, nullable=True, index=True)
    strategy_tag = Column(String, nullable=True, index=True)
    entry_time = Column(DateTime, nullable=False, index=True)
    exit_time = Column(DateTime, nullable=True)
    emotion_tag = Column(String, default="Neutral")
    notes = Column(Text, nullable=True)
    planned_stop_loss = Column(Float, nullable=True)
    planned_target = Column(Float, nullable=True)
    screenshot_url = Column(String, nullable=True)
    status = Column(String, default="closed")
    gross_pnl = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)
    total_charges = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    legs = relationship(
        "LegModel", back_populates="trade", cascade="all, delete-orphan"
    )
    fills = relationship(
        "FillModel", back_populates="trade", cascade="all, delete-orphan"
    )
    charges = relationship(
        "ChargesModel",
        uselist=False,
        back_populates="trade",
        cascade="all, delete-orphan",
    )


class LegModel(Base):
    __tablename__ = "legs"

    leg_id = Column(String, primary_key=True, index=True)
    trade_id = Column(String, ForeignKey("trades.id"), index=True)
    instrument = Column(String, nullable=False)
    segment = Column(String, nullable=False)  # "Equity", "Futures", "CE", "PE"
    side = Column(String, nullable=False)  # "buy", "sell"
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    lot_size = Column(Integer, default=1)
    order_id = Column(String, nullable=True)
    fill_time = Column(DateTime, nullable=False)
    is_delivery = Column(Boolean, default=False)

    trade = relationship("TradeModel", back_populates="legs")


class FillModel(Base):
    __tablename__ = "fills"

    fill_id = Column(String, primary_key=True, index=True)
    trade_id = Column(String, ForeignKey("trades.id"), index=True)
    leg_id = Column(String, nullable=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    fill_time = Column(DateTime, nullable=False)

    trade = relationship("TradeModel", back_populates="fills")


class ChargesModel(Base):
    __tablename__ = "charges"

    trade_id = Column(String, ForeignKey("trades.id"), primary_key=True)
    brokerage = Column(Float, default=0.0)
    stt = Column(Float, default=0.0)
    exchange_txn_charge = Column(Float, default=0.0)
    gst = Column(Float, default=0.0)
    sebi_charges = Column(Float, default=0.0)
    stamp_duty = Column(Float, default=0.0)
    dp_charges = Column(Float, default=0.0)
    total_charges = Column(Float, default=0.0)

    trade = relationship("TradeModel", back_populates="charges")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
