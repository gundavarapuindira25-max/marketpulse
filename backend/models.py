"""
SQLAlchemy models — the Postgres schema for MarketPulse.

One parent entity, four children (one-to-many each):
  - products                one row per trading pair (e.g. BTC-USD)
  - candles                 closed 1-min OHLCV bars, FK -> products
  - order_book_snapshots    periodic top-of-book snapshots, FK -> products
  - trades                  each ticker trade event, FK -> products
  - narrations              every narrator attempt, grounded or rejected, FK -> products

Schema changes go through Alembic migrations (see backend/alembic/), not
auto-create-on-boot — same discipline as Liquibase-managed schemas.
"""

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    """A trading pair, e.g. "BTC-USD". Parent side of the one-to-many
    relationship to every other table — one product has many candles,
    many trades, many snapshots, many narrations."""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True)

    candles: Mapped[list["Candle"]] = relationship(back_populates="product")
    snapshots: Mapped[list["OrderBookSnapshot"]] = relationship(back_populates="product")
    trades: Mapped[list["Trade"]] = relationship(back_populates="product")
    narrations: Mapped[list["Narration"]] = relationship(back_populates="product")


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (UniqueConstraint("product_id", "ts", name="uq_candles_product_ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    ts: Mapped[int] = mapped_column(BigInteger)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)

    product: Mapped["Product"] = relationship(back_populates="candles")


class OrderBookSnapshot(Base):
    __tablename__ = "order_book_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    ts: Mapped[float] = mapped_column(Float, index=True)
    best_bid: Mapped[float | None] = mapped_column(Float)
    best_ask: Mapped[float | None] = mapped_column(Float)
    spread: Mapped[float | None] = mapped_column(Float)
    mid_price: Mapped[float | None] = mapped_column(Float)
    bids: Mapped[list] = mapped_column(JSONB)  # top-N [{price, size}, ...]
    asks: Mapped[list] = mapped_column(JSONB)

    product: Mapped["Product"] = relationship(back_populates="snapshots")


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    ts: Mapped[float] = mapped_column(Float, index=True)
    price: Mapped[float] = mapped_column(Float)
    side: Mapped[str | None] = mapped_column(String)
    size: Mapped[float | None] = mapped_column(Float)

    product: Mapped["Product"] = relationship(back_populates="trades")


class Narration(Base):
    """One row per narrator attempt — including rejected ones, with the
    offending numbers recorded, so the grounding check's behavior over time
    is itself queryable (not just visible in logs)."""
    __tablename__ = "narrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    ts: Mapped[float] = mapped_column(Float, index=True)
    text: Mapped[str | None] = mapped_column(Text)
    grounded: Mapped[bool] = mapped_column(Boolean)
    offending_numbers: Mapped[list | None] = mapped_column(JSONB)

    product: Mapped["Product"] = relationship(back_populates="narrations")
