"""
MarketPulse — Live Order Book Visualizer
Backend: FastAPI + WebSocket fan-out from Coinbase Advanced Trade feed
"""

import asyncio
import json
import os
import ssl
import time
from typing import Optional

import certifi
import ollama
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import storage
from narrator import generate_narration

load_dotenv()

app = FastAPI(title="MarketPulse API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory order book state
# ---------------------------------------------------------------------------

PRODUCT_ID = os.getenv("PRODUCT_ID", "BTC-USD")
COINBASE_WS_URL = "wss://advanced-trade-ws.coinbase.com"
NARRATION_INTERVAL_SECONDS = int(os.getenv("NARRATION_INTERVAL_SECONDS", "45"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

ollama_client = ollama.AsyncClient(host=OLLAMA_HOST)

class OrderBook:
    def __init__(self):
        self.bids: dict[str, float] = {}   # price -> size
        self.asks: dict[str, float] = {}
        self.last_price: Optional[float] = None
        self.last_trade_side: Optional[str] = None
        self.sequence: int = 0

    def apply_update(self, updates: list[dict]) -> None:
        for update in updates:
            side = update["side"]
            price = update["price_level"]
            size = float(update["new_quantity"])
            book = self.bids if side == "bid" else self.asks
            if size == 0.0:
                book.pop(price, None)
            else:
                book[price] = size

    def snapshot(self) -> dict:
        sorted_bids = sorted(self.bids.items(), key=lambda x: float(x[0]), reverse=True)[:20]
        sorted_asks = sorted(self.asks.items(), key=lambda x: float(x[0]))[:20]

        best_bid = float(sorted_bids[0][0]) if sorted_bids else None
        best_ask = float(sorted_asks[0][0]) if sorted_asks else None
        spread = round(best_ask - best_bid, 2) if best_bid and best_ask else None
        mid_price = round((best_bid + best_ask) / 2, 2) if best_bid and best_ask else None

        return {
            "type": "order_book",
            "product": PRODUCT_ID,
            "bids": [{"price": float(p), "size": s} for p, s in sorted_bids],
            "asks": [{"price": float(p), "size": s} for p, s in sorted_asks],
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "mid_price": mid_price,
            "last_price": self.last_price,
            "last_trade_side": self.last_trade_side,
            "server_ts": time.time(),
        }


order_book = OrderBook()

# ---------------------------------------------------------------------------
# 1-minute OHLCV candle aggregation
# ---------------------------------------------------------------------------

class CandleAggregator:
    """Buckets ticks into 1-minute OHLCV candles.

    Per-tick trade volume isn't exposed by the ticker feed, so volume is
    approximated from the delta between consecutive `volume_24h` readings
    (same approach used for the VWAP overlay on the price chart).
    """

    def __init__(self):
        self.current: Optional[dict] = None
        self.prev_volume_24h: Optional[float] = None

    def update(self, price: float, volume_24h: Optional[float]) -> Optional[dict]:
        bucket_ts = int(time.time() // 60) * 60

        delta_vol = 0.0
        if volume_24h is not None and self.prev_volume_24h is not None:
            delta_vol = max(0.0, volume_24h - self.prev_volume_24h)
        if volume_24h is not None:
            self.prev_volume_24h = volume_24h

        closed = None
        if self.current is None or self.current["ts"] != bucket_ts:
            closed = self.current
            self.current = {
                "ts": bucket_ts,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": delta_vol,
            }
        else:
            c = self.current
            c["high"] = max(c["high"], price)
            c["low"] = min(c["low"], price)
            c["close"] = price
            c["volume"] += delta_vol

        return closed


candle_agg = CandleAggregator()

# ---------------------------------------------------------------------------
# Connected frontend clients
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)


manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Coinbase WebSocket consumer (runs as background task)
# ---------------------------------------------------------------------------

async def coinbase_feed():
    subscribe_msg = {
        "type": "subscribe",
        "product_ids": [PRODUCT_ID],
        "channel": "level2",
    }

    ticker_msg = {
        "type": "subscribe",
        "product_ids": [PRODUCT_ID],
        "channel": "ticker",
    }

    while True:
        try:
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            async with websockets.connect(COINBASE_WS_URL, ssl=ssl_ctx, ping_interval=20, max_size=10 * 1024 * 1024) as ws:
                await ws.send(json.dumps(subscribe_msg))
                await ws.send(json.dumps(ticker_msg))
                print(f"[coinbase] Subscribed to {PRODUCT_ID} level2 + ticker")

                async for raw in ws:
                    msg = json.loads(raw)
                    channel = msg.get("channel")
                    events = msg.get("events", [])

                    for event in events:
                        etype = event.get("type")

                        # Order book snapshot or update
                        if channel == "l2_data":
                            updates = event.get("updates", [])
                            order_book.apply_update(updates)
                            snapshot = order_book.snapshot()
                            await manager.broadcast(snapshot)

                        # Ticker — last trade price
                        elif channel == "ticker":
                            tickers = event.get("tickers", [])
                            for t in tickers:
                                order_book.last_price = float(t.get("price", 0) or 0)
                                order_book.last_trade_side = t.get("side")
                                volume_24h_raw = t.get("volume_24_h")
                                tick = {
                                    "type": "ticker",
                                    "product": PRODUCT_ID,
                                    "price": order_book.last_price,
                                    "side": order_book.last_trade_side,
                                    "volume_24h": volume_24h_raw,
                                    "high_24h": t.get("high_24_h"),
                                    "low_24h": t.get("low_24_h"),
                                    "server_ts": time.time(),
                                }
                                await manager.broadcast(tick)

                                volume_24h = float(volume_24h_raw) if volume_24h_raw else None
                                closed_candle = candle_agg.update(order_book.last_price, volume_24h)
                                if closed_candle:
                                    storage.save_candle(PRODUCT_ID, closed_candle)
                                await manager.broadcast({
                                    "type": "candle",
                                    "product": PRODUCT_ID,
                                    "candle": candle_agg.current,
                                    "server_ts": time.time(),
                                })

        except Exception as e:
            print(f"[coinbase] Connection error: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


# ---------------------------------------------------------------------------
# LLM market narrator (runs on a timer, independent of the tick rate)
# ---------------------------------------------------------------------------

async def narrator_loop():
    while True:
        await asyncio.sleep(NARRATION_INTERVAL_SECONDS)

        if order_book.last_price is None:
            continue  # no data yet, nothing to narrate

        recent_candles = storage.get_recent_candles(PRODUCT_ID, limit=10)
        text = await generate_narration(ollama_client, order_book.snapshot(), recent_candles, PRODUCT_ID)
        if text:
            await manager.broadcast({
                "type": "narration",
                "product": PRODUCT_ID,
                "text": text,
                "server_ts": time.time(),
            })


# ---------------------------------------------------------------------------
# FastAPI lifecycle + routes
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup():
    asyncio.create_task(coinbase_feed())
    asyncio.create_task(narrator_loop())


@app.get("/health")
def health():
    return {"status": "ok", "product": PRODUCT_ID}


@app.get("/candles")
def get_candles(limit: int = 200):
    return {"product": PRODUCT_ID, "candles": storage.get_recent_candles(PRODUCT_ID, limit)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send current snapshot immediately on connect
    await websocket.send_text(json.dumps(order_book.snapshot()))
    try:
        while True:
            # Keep connection alive; client doesn't need to send anything
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
