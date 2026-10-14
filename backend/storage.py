"""
Postgres persistence for MarketPulse — products, candles, order book
snapshots, trades, and every narrator attempt (grounded or rejected).

Schema is managed entirely through Alembic migrations (backend/alembic/),
not created here — same discipline as a Liquibase-managed schema.
"""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db import async_session
from models import Candle, Narration, OrderBookSnapshot, Product, Trade

# In-process cache: the app only ever streams one product per run (set via
# PRODUCT_ID), so there's no point re-querying its id on every single write.
_product_id_cache: dict[str, int] = {}


async def _get_or_create_product_id(symbol: str) -> int:
    if symbol in _product_id_cache:
        return _product_id_cache[symbol]

    async with async_session() as session:
        stmt = pg_insert(Product).values(symbol=symbol).on_conflict_do_nothing(index_elements=["symbol"])
        await session.execute(stmt)
        await session.commit()

        result = await session.execute(select(Product.id).where(Product.symbol == symbol))
        product_id = result.scalar_one()

    _product_id_cache[symbol] = product_id
    return product_id


async def save_candle(product: str, candle: dict) -> None:
    """Candles are only saved once closed, so the ON CONFLICT path isn't hit
    in normal operation — kept as a defensive upsert (e.g. a restart replaying
    the same bucket), preserving the running high/low via GREATEST/LEAST
    rather than overwriting, same as the previous SQLite version."""
    product_id = await _get_or_create_product_id(product)
    stmt = pg_insert(Candle).values(
        product_id=product_id,
        ts=candle["ts"],
        open=candle["open"],
        high=candle["high"],
        low=candle["low"],
        close=candle["close"],
        volume=candle["volume"],
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_candles_product_ts",
        set_={
            "high": func.greatest(Candle.high, stmt.excluded.high),
            "low": func.least(Candle.low, stmt.excluded.low),
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
        },
    )
    async with async_session() as session:
        await session.execute(stmt)
        await session.commit()


async def get_recent_candles(product: str, limit: int = 200) -> list[dict]:
    async with async_session() as session:
        result = await session.execute(
            select(Candle.ts, Candle.open, Candle.high, Candle.low, Candle.close, Candle.volume)
            .join(Product, Product.id == Candle.product_id)
            .where(Product.symbol == product)
            .order_by(Candle.ts.desc())
            .limit(limit)
        )
        rows = result.all()
    rows.reverse()
    return [
        {"ts": ts, "open": o, "high": h, "low": l, "close": c, "volume": v}
        for ts, o, h, l, c, v in rows
    ]


async def save_order_book_snapshot(product: str, snapshot: dict) -> None:
    product_id = await _get_or_create_product_id(product)
    async with async_session() as session:
        session.add(OrderBookSnapshot(
            product_id=product_id,
            ts=snapshot["server_ts"],
            best_bid=snapshot.get("best_bid"),
            best_ask=snapshot.get("best_ask"),
            spread=snapshot.get("spread"),
            mid_price=snapshot.get("mid_price"),
            bids=snapshot.get("bids", []),
            asks=snapshot.get("asks", []),
        ))
        await session.commit()


async def save_trade(product: str, ts: float, price: float, side: str | None, size: float | None) -> None:
    product_id = await _get_or_create_product_id(product)
    async with async_session() as session:
        session.add(Trade(product_id=product_id, ts=ts, price=price, side=side, size=size))
        await session.commit()


async def save_narration(
    product: str, ts: float, text: str | None, grounded: bool, offending: list | None
) -> None:
    product_id = await _get_or_create_product_id(product)
    async with async_session() as session:
        session.add(Narration(
            product_id=product_id, ts=ts, text=text, grounded=grounded, offending_numbers=offending or None,
        ))
        await session.commit()
