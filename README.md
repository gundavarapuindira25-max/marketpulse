# MarketPulse — Live Order Book Visualizer

Real-time order book and price chart for BTC-USD, streaming directly from the Coinbase Advanced Trade WebSocket API.

Built to demonstrate low-latency market data architecture: a Python backend consumes the exchange feed and fans out to all connected browser clients over WebSockets, with sub-100ms end-to-end latency displayed live in the UI.

![stack](https://img.shields.io/badge/Python-FastAPI-green) ![stack](https://img.shields.io/badge/React-Recharts-blue) ![stack](https://img.shields.io/badge/WebSockets-real--time-orange)

---

## Features

- Live bid/ask order book (top 20 levels) with depth visualization bars
- Real-time tick price chart with SMA-20 and VWAP overlays
- 1-minute OHLCV candlestick chart, persisted to SQLite so history survives a restart
- Trade tape, spread history, and order book depth chart
- 24h high, low, volume ticker strip
- Live spread and mid-price calculation
- End-to-end latency display (exchange → backend → browser)
- Auto-reconnect on connection drop
- Configurable trading pair via environment variable

## Architecture

```
Coinbase Advanced Trade WS
        │  level2 + ticker channels
        ▼
  FastAPI backend (Python)
  ├── OrderBook — in-memory bid/ask state
  ├── CandleAggregator — buckets ticks into 1-min OHLCV candles
  ├── storage.py — persists closed candles to SQLite
  ├── ConnectionManager — fan-out to N browser clients
  ├── /ws WebSocket endpoint
  └── /candles REST endpoint — recent candle history
        │
        ▼
  React frontend
  ├── TickerBar — 24h stats
  ├── PriceChart — live Recharts area chart + SMA20/VWAP
  ├── CandleChart — 1-min OHLCV candlestick chart
  └── OrderBook — depth-bar visualization
```

## Quick Start

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optionally change PRODUCT_ID
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PRODUCT_ID` | `BTC-USD` | Trading pair to stream. E.g. `ETH-USD`, `SOL-USD` |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, websockets, asyncio |
| Frontend | React, Recharts, Vite |
| Data source | Coinbase Advanced Trade WebSocket API (public, no auth required) |
