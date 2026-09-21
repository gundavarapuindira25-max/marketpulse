import { useEffect, useRef, useState } from "react";
import OrderBook from "./components/OrderBook";
import TickerBar from "./components/TickerBar";
import MarketNarrator from "./components/MarketNarrator";
import PriceChart from "./components/PriceChart";
import TradeTape from "./components/TradeTape";
import DepthChart from "./components/DepthChart";
import SpreadChart from "./components/SpreadChart";
import SessionStats from "./components/SessionStats";
import CandleChart from "./components/CandleChart";
import "./App.css";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const MAX_TICKS = 300;
const MAX_TRADES = 50;
const MAX_SPREADS = 200;
const MAX_CANDLES = 200;

export default function App() {
  const [page, setPage] = useState("terminal"); // "terminal" | "analytics"
  const [orderBook, setOrderBook] = useState({ bids: [], asks: [], spread: null, mid_price: null });
  const [ticker, setTicker] = useState(null);
  const [ticks, setTicks] = useState([]);
  const [trades, setTrades] = useState([]);       // recent trades for tape
  const [spreads, setSpreads] = useState([]);     // spread history
  const [candles, setCandles] = useState([]);     // 1-min OHLCV candles
  const [narration, setNarration] = useState(null); // { text, ts } — latest LLM market summary
  const [sessionStats, setSessionStats] = useState({ tradeCount: 0, totalVolume: 0, minPrice: null, maxPrice: null, startTime: Date.now() });
  const [latency, setLatency] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const lastVolumeRef = useRef(null);

  useEffect(() => {
    fetch(`${API_URL}/candles?limit=${MAX_CANDLES}`)
      .then((r) => r.json())
      .then((data) => setCandles(data.candles || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 2000);
      };

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        const now = Date.now() / 1000;
        const lat = msg.server_ts ? Math.round((now - msg.server_ts) * 1000) : null;
        if (lat !== null) setLatency(lat);

        if (msg.type === "order_book") {
          setOrderBook({
            bids: msg.bids,
            asks: msg.asks,
            spread: msg.spread,
            mid_price: msg.mid_price,
            best_bid: msg.best_bid,
            best_ask: msg.best_ask,
          });
          // Track spread history
          if (msg.spread != null) {
            setSpreads((prev) => {
              const next = [...prev, { time: now, spread: msg.spread }];
              return next.length > MAX_SPREADS ? next.slice(-MAX_SPREADS) : next;
            });
          }
        } else if (msg.type === "ticker") {
          setTicker(msg);
          const price = msg.price;
          const volume24h = parseFloat(msg.volume_24h || 0);
          const prevVolume = lastVolumeRef.current;
          const size = prevVolume !== null ? Math.max(0, volume24h - prevVolume) : 0;
          lastVolumeRef.current = volume24h;

          if (price) {
            const tick = { time: now, price, size };
            setTicks((prev) => {
              const next = [...prev, tick];
              return next.length > MAX_TICKS ? next.slice(-MAX_TICKS) : next;
            });

            // Trade tape entry
            setTrades((prev) => {
              const entry = { time: now, price, side: msg.side, id: now + Math.random() };
              const next = [entry, ...prev];
              return next.length > MAX_TRADES ? next.slice(0, MAX_TRADES) : next;
            });

            // Session stats
            setSessionStats((prev) => ({
              ...prev,
              tradeCount: prev.tradeCount + 1,
              minPrice: prev.minPrice === null ? price : Math.min(prev.minPrice, price),
              maxPrice: prev.maxPrice === null ? price : Math.max(prev.maxPrice, price),
            }));
          }
        } else if (msg.type === "narration") {
          setNarration({ text: msg.text, ts: Date.now() });
        } else if (msg.type === "candle") {
          setCandles((prev) => {
            if (!prev.length || prev[prev.length - 1].ts !== msg.candle.ts) {
              const next = [...prev, msg.candle];
              return next.length > MAX_CANDLES ? next.slice(-MAX_CANDLES) : next;
            }
            return [...prev.slice(0, -1), msg.candle];
          });
        }
      };
    }

    connect();
    return () => wsRef.current?.close();
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <span className="logo">MarketPulse</span>
          <span className="product-tag">BTC-USD</span>
          <nav className="page-nav">
            <button
              className={`nav-btn ${page === "terminal" ? "active" : ""}`}
              onClick={() => setPage("terminal")}
            >
              Terminal
            </button>
            <button
              className={`nav-btn ${page === "analytics" ? "active" : ""}`}
              onClick={() => setPage("analytics")}
            >
              Analytics
            </button>
          </nav>
        </div>
        <div className="header-right">
          <span className={`status-dot ${connected ? "connected" : "disconnected"}`} />
          <span className="status-label">{connected ? "Live" : "Reconnecting..."}</span>
          {latency !== null && <span className="latency">{latency}ms</span>}
        </div>
      </header>

      <TickerBar ticker={ticker} />
      <MarketNarrator narration={narration} />

      {page === "terminal" && (
        <main className="main-grid">
          {/* Left column: chart + trade tape */}
          <div className="left-col">
            <section className="panel chart-panel">
              <h2 className="panel-title">Price + VWAP</h2>
              <PriceChart ticks={ticks} />
            </section>
            <section className="panel tape-panel">
              <h2 className="panel-title">Recent Trades</h2>
              <TradeTape trades={trades} />
            </section>
          </div>

          {/* Right column: order book */}
          <section className="panel book-panel">
            <h2 className="panel-title">
              Order Book
              {orderBook.spread && (
                <span className="spread-badge">Spread: ${orderBook.spread}</span>
              )}
            </h2>
            <OrderBook bids={orderBook.bids} asks={orderBook.asks} midPrice={orderBook.mid_price} />
          </section>
        </main>
      )}

      {page === "analytics" && (
        <main className="analytics-grid">
          <section className="panel">
            <h2 className="panel-title">Session Stats</h2>
            <SessionStats stats={sessionStats} ticker={ticker} />
          </section>
          <section className="panel">
            <h2 className="panel-title">Spread History</h2>
            <SpreadChart spreads={spreads} />
          </section>
          <section className="panel candle-panel">
            <h2 className="panel-title">1-Min Candles</h2>
            <CandleChart candles={candles} />
          </section>
          <section className="panel depth-panel">
            <h2 className="panel-title">Order Book Depth</h2>
            <DepthChart bids={orderBook.bids} asks={orderBook.asks} />
          </section>
        </main>
      )}
    </div>
  );
}
