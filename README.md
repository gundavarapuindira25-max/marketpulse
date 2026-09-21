# MarketPulse — Live Order Book Visualizer

Real-time order book and price chart for BTC-USD, streaming directly from the Coinbase Advanced Trade WebSocket API.

Built to demonstrate low-latency market data architecture: a Python backend consumes the exchange feed and fans out to all connected browser clients over WebSockets, with sub-100ms end-to-end latency displayed live in the UI.

![stack](https://img.shields.io/badge/Python-FastAPI-green) ![stack](https://img.shields.io/badge/React-Recharts-blue) ![stack](https://img.shields.io/badge/WebSockets-real--time-orange) ![stack](https://img.shields.io/badge/LLM-Ollama-purple)

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
- **AI market narrator** — a local LLM (Ollama) turns the live order book + recent candles into a short plain-English summary every 45s, grounded strictly in the real numbers on screen (no invented prices, no trading advice). Runs fully offline, no API key or cost.

## Architecture

```
Coinbase Advanced Trade WS          Ollama (local LLM)
        │  level2 + ticker channels        ▲  llama3.2:3b
        ▼                                  │  every 45s
  FastAPI backend (Python)                 │
  ├── OrderBook — in-memory bid/ask state ─┘
  ├── CandleAggregator — buckets ticks into 1-min OHLCV candles
  ├── storage.py — persists closed candles to SQLite
  ├── narrator.py — grounded market summary via local LLM
  ├── ConnectionManager — fan-out to N browser clients
  ├── /ws WebSocket endpoint
  └── /candles REST endpoint — recent candle history
        │
        ▼
  React frontend
  ├── TickerBar — 24h stats
  ├── MarketNarrator — live LLM-generated market summary
  ├── PriceChart — live Recharts area chart + SMA20/VWAP
  ├── CandleChart — 1-min OHLCV candlestick chart
  └── OrderBook — depth-bar visualization
```

## Quick Start

### LLM narrator (Ollama)

The market narrator runs against a local model — no API key needed. Install and start it before running the backend:

```bash
brew install ollama
brew services start ollama     # or: ollama serve
ollama pull llama3.2:3b
```

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optionally change PRODUCT_ID, OLLAMA_MODEL, etc.
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
| `OLLAMA_HOST` | `http://localhost:11434` | Where the Ollama server is running |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model used for market narration |
| `NARRATION_INTERVAL_SECONDS` | `45` | How often a new market summary is generated |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, websockets, asyncio |
| Frontend | React, Recharts, Vite |
| Data source | Coinbase Advanced Trade WebSocket API (public, no auth required) |
| LLM narrator | Ollama (local), `llama3.2:3b` — no API key, no cost, runs offline |
