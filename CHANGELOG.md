# Changelog

All notable changes to MarketPulse are tracked here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## 2026-07-22 — 1-minute candle history

### Added
- **1-minute OHLCV candle aggregation** in the backend (`CandleAggregator` in `main.py`), bucketing ticks by minute; volume is approximated the same way as the VWAP overlay, from the delta between consecutive `volume_24h` readings
- **SQLite persistence** for closed candles (`storage.py`) so history survives a backend restart
- **`GET /candles`** REST endpoint serving recent candle history for initial chart load
- **Candlestick chart** (`CandleChart.jsx`) on the Analytics page, fed by the REST history on mount and live `candle` WebSocket messages thereafter

### Changed
- `backend/main.py` restored and extended (previous session had renamed it to `main_old.py` mid-refactor without finishing the rewrite — merged the candle aggregation in and removed the old file)
- Added `certifi` to `requirements.txt` (was imported by `main.py` but missing from the pinned deps)

## 2026-07-21 — Trading terminal expansion

Added the panels needed to make the app feel like a real trading terminal instead of a single-chart demo, and split the UI into two pages.

### Added
- **VWAP overlay** on the price chart, derived by approximating per-tick trade volume from the delta between consecutive `volume_24h` readings (the ticker feed doesn't expose per-trade size directly)
- **Trade tape** (`TradeTape.jsx`) — scrolling feed of the last 50 trades with color-coded buy/sell direction
- **Depth chart** (`DepthChart.jsx`) — cumulative bid/ask liquidity by price, step-area style
- **Spread history chart** (`SpreadChart.jsx`) — bid/ask spread over time
- **Session stats panel** (`SessionStats.jsx`) — session duration, trades seen, session high/low, current price, 24h volume
- **Analytics page** (`/analytics`) housing session stats, spread history, and the depth chart
- **Header nav** — Terminal / Analytics buttons to switch pages
- Chart legend (Price / SMA20 / VWAP) on the price chart

### Fixed
- Large empty whitespace under the price chart — it was rendering at a fixed 260px height inside a taller flex cell. Chart panels now use a flex-fill layout (`chart-fill` / `chart-body`) so the chart occupies its full panel height.

### Changed
- Left column of the Terminal page now stacks the price chart (VWAP) above the trade tape instead of the chart alone
- `MAX_TICKS` raised from 200 to 300; added `MAX_TRADES` (50) and `MAX_SPREADS` (200) buffers

## 2026-07-21 — Initial build

### Added
- FastAPI backend consuming Coinbase Advanced Trade WebSocket (`level2` + `ticker` channels), maintaining in-memory order book state and fanning out to connected browser clients over `/ws`
- React frontend: `TickerBar` (24h stats), `PriceChart` (live tick chart with SMA-20), `OrderBook` (top-20 bid/ask depth bars)
- Live spread and mid-price calculation
- End-to-end latency display (exchange → backend → browser)
- Auto-reconnect on WebSocket drop
- Configurable trading pair via `PRODUCT_ID` env var
