# MarketPulse — Live Order Book Visualizer

Real-time order book and price chart for BTC-USD, streaming directly from the Coinbase Advanced Trade WebSocket API.

Built to demonstrate low-latency market data architecture: a Python backend consumes the exchange feed and fans out to all connected browser clients over WebSockets, with sub-100ms end-to-end latency displayed live in the UI.

![stack](https://img.shields.io/badge/Python-FastAPI-green) ![stack](https://img.shields.io/badge/React-Recharts-blue) ![stack](https://img.shields.io/badge/WebSockets-real--time-orange) ![stack](https://img.shields.io/badge/LLM-Ollama-purple) ![stack](https://img.shields.io/badge/DB-PostgreSQL-336791)

---

## Features

- Live bid/ask order book (top 20 levels) with depth visualization bars
- Real-time tick price chart with SMA-20 and VWAP overlays
- 1-minute OHLCV candlestick chart, persisted to Postgres so history survives a restart
- Postgres-backed persistence: candles, periodic order book snapshots, every trade tick, and every narrator attempt (grounded or rejected) all land in a real relational schema, managed through Alembic migrations and queryable directly with SQL
- Trade tape, spread history, and order book depth chart
- 24h high, low, volume ticker strip
- Live spread and mid-price calculation
- End-to-end latency display (exchange → backend → browser)
- Auto-reconnect on connection drop
- Configurable trading pair via environment variable
- AI market narrator: a local LLM (Ollama) turns the live order book + recent candles into a short plain-English summary every 45s, grounded strictly in the real numbers on screen (no invented prices, no trading advice). Runs fully offline, no API key or cost.
- Deterministic hallucination guard: every number the narrator states is cross-checked against the actual order book/candle data it was given; a narration containing a price or level that doesn't match the real data is rejected before it ever reaches the browser, not just discouraged by the prompt.

## Architecture

```
Coinbase Advanced Trade WS          Ollama (local LLM)
        │  level2 + ticker channels        ▲  llama3.2:3b
        ▼                                  │  every 45s
  FastAPI backend (Python)                 │
  ├── OrderBook — in-memory bid/ask state ─┘
  ├── CandleAggregator — buckets ticks into 1-min OHLCV candles
  ├── snapshot_loop() — persists an order book snapshot every 10s
  ├── storage.py — async SQLAlchemy persistence (candles, snapshots, trades, narrations)
  ├── narrator.py — grounded market summary via local LLM
  ├── validation.py — rejects narrations whose numbers don't match real data
  ├── ConnectionManager — fan-out to N browser clients
  ├── /ws WebSocket endpoint
  └── /candles REST endpoint — recent candle history
        │
        ▼
  PostgreSQL (Docker)
  ├── candles                 closed 1-min OHLCV bars
  ├── order_book_snapshots    periodic top-of-book state (JSONB bid/ask levels)
  ├── trades                  every ticker trade event
  └── narrations              every narrator attempt — grounded or rejected

  React frontend
  ├── TickerBar — 24h stats
  ├── MarketNarrator — live LLM-generated market summary
  ├── PriceChart — live Recharts area chart + SMA20/VWAP
  ├── CandleChart — 1-min OHLCV candlestick chart
  └── OrderBook — depth-bar visualization
```

## Hallucination guard

`validation.py` confirms every number the narrator states is real: each figure in the generated narration is extracted and cross-checked against the exact order book/candle snapshot the model was shown, with a small tolerance to allow for rounding. A narration where every number checks out gets broadcast; one with a mismatch is rejected for that cycle and logged with the offending value(s).

The check excludes numbers in hyphenated units like "1-minute" or "24-hour" so everyday phrasing isn't mistaken for a market-data claim, verified across repeated test batches with zero false positives.

## Database

Persistence runs on PostgreSQL (local, via Docker), not SQLite: a real relational schema instead of a single candles table, with schema changes tracked through Alembic migrations rather than created ad hoc on boot.

Schema (`backend/models.py`):

| Table | What it holds |
|---|---|
| `candles` | Closed 1-minute OHLCV bars |
| `order_book_snapshots` | Top-of-book state (best bid/ask, spread, mid-price) every 10s, with the top levels stored as JSONB |
| `trades` | Every ticker trade event: price, side, timestamp |
| `narrations` | Every narrator attempt, grounded or rejected, with the offending numbers recorded for rejected ones, so the hallucination guard's behavior over time is itself queryable, not just visible in logs |

Running it:

```bash
docker compose up -d                 # starts Postgres on localhost:5432
cd backend
alembic upgrade head                 # applies the schema
```

Querying it directly:

```bash
docker exec -it marketpulse-postgres psql -U marketpulse -d marketpulse
```

```sql
-- How often has the hallucination guard actually rejected something?
SELECT grounded, count(*) FROM narrations GROUP BY grounded;

-- Biggest price move in the last hour
SELECT max(high) - min(low) AS range FROM candles WHERE ts > extract(epoch from now() - interval '1 hour');

-- Spread over time
SELECT ts, spread FROM order_book_snapshots ORDER BY ts DESC LIMIT 20;
```

Schema changes going forward go through a new Alembic revision (`alembic revision --autogenerate -m "..."`, reviewed, then `alembic upgrade head`) rather than editing tables by hand.

## Quick Start

### LLM narrator (Ollama)

The market narrator runs against a local model with no API key needed. Install and start it before running the backend:

```bash
brew install ollama
brew services start ollama     # or: ollama serve
ollama pull llama3.2:3b
```

### Database (Postgres)

```bash
docker compose up -d          # from the project root
cd backend
alembic upgrade head          # applies the schema (see Database section above)
```

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optionally change PRODUCT_ID, OLLAMA_MODEL, DATABASE_URL, etc.
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
| `DATABASE_URL` | `postgresql+asyncpg://marketpulse:marketpulse@localhost:5432/marketpulse` | Postgres connection string |
| `SNAPSHOT_INTERVAL_SECONDS` | `10` | How often an order book snapshot is persisted |
| `OLLAMA_HOST` | `http://localhost:11434` | Where the Ollama server is running |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model used for market narration |
| `NARRATION_INTERVAL_SECONDS` | `45` | How often a new market summary is generated |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, websockets, asyncio |
| Database | PostgreSQL (Docker), SQLAlchemy (async), Alembic migrations |
| Frontend | React, Recharts, Vite |
| Data source | Coinbase Advanced Trade WebSocket API (public, no auth required) |
| LLM narrator | Ollama (local), `llama3.2:3b` — no API key, no cost, runs offline |
