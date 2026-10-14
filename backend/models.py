"""
SQLAlchemy models — the Postgres schema for MarketPulse.

Four tables, each one a different angle on the live feed:
  - candles                closed 1-min OHLCV bars (was SQLite before; same shape)
  - order_book_snapshots   periodic snapshots of top-of-book state (new)
  - trades                 each ticker trade event (new)
  - narrations             every narrator attempt, grounded or rejected (new)

Schema changes go through Alembic migrations (see backend/alembic/), not
auto-create-on-boot — same discipline as Liquibase-managed schemas.
"""

from sqlalchemy import BigInteger, Boolean, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (UniqueConstraint("product", "ts", name="uq_candles_product_ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product: Mapped[str] = mapped_column(String, index=True)
    ts: Mapped[int] = mapped_column(BigInteger)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)


class OrderBookSnapshot(Base):
    __tablename__ = "order_book_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product: Mapped[str] = mapped_column(String, index=True)
    ts: Mapped[float] = mapped_column(Float, index=True)
    best_bid: Mapped[float | None] = mapped_column(Float)
    best_ask: Mapped[float | None] = mapped_column(Float)
    spread: Mapped[float | None] = mapped_column(Float)
    mid_price: Mapped[float | None] = mapped_column(Float)
    bids: Mapped[list] = mapped_column(JSONB)  # top-N [{price, size}, ...]
    asks: Mapped[list] = mapped_column(JSONB)


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product: Mapped[str] = mapped_column(String, index=True)
    ts: Mapped[float] = mapped_column(Float, index=True)
    price: Mapped[float] = mapped_column(Float)
    side: Mapped[str | None] = mapped_column(String)
    size: Mapped[float | None] = mapped_column(Float)


class Narration(Base):
    """One row per narrator attempt — including rejected ones, with the
    offending numbers recorded, so the grounding check's behavior over time
    is itself queryable (not just visible in logs)."""
    __tablename__ = "narrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product: Mapped[str] = mapped_column(String, index=True)
    ts: Mapped[float] = mapped_column(Float, index=True)
    text: Mapped[str | None] = mapped_column(Text)
    grounded: Mapped[bool] = mapped_column(Boolean)
    offending_numbers: Mapped[list | None] = mapped_column(JSONB)
