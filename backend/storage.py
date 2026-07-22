"""
SQLite persistence for closed 1-minute OHLCV candles.

Writes are infrequent (one per product per minute) so a single
lock-guarded connection is simpler and just as correct as an async
driver here.
"""

import os
import sqlite3
import threading

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "marketpulse.db"))

_lock = threading.Lock()
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.execute(
    """
    CREATE TABLE IF NOT EXISTS candles (
        product TEXT NOT NULL,
        ts INTEGER NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume REAL NOT NULL,
        PRIMARY KEY (product, ts)
    )
    """
)
_conn.commit()


def save_candle(product: str, candle: dict) -> None:
    with _lock:
        _conn.execute(
            """
            INSERT INTO candles (product, ts, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product, ts) DO UPDATE SET
                high = MAX(high, excluded.high),
                low = MIN(low, excluded.low),
                close = excluded.close,
                volume = excluded.volume
            """,
            (product, candle["ts"], candle["open"], candle["high"], candle["low"], candle["close"], candle["volume"]),
        )
        _conn.commit()


def get_recent_candles(product: str, limit: int = 200) -> list[dict]:
    with _lock:
        rows = _conn.execute(
            """
            SELECT ts, open, high, low, close, volume FROM candles
            WHERE product = ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (product, limit),
        ).fetchall()
    rows.reverse()
    return [
        {"ts": ts, "open": o, "high": h, "low": l, "close": c, "volume": v}
        for ts, o, h, l, c, v in rows
    ]
