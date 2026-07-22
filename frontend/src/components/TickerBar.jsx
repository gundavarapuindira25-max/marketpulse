/**
 * TickerBar — 24h stats strip across the top
 */
export default function TickerBar({ ticker }) {
  if (!ticker) return <div className="ticker-bar ticker-bar--empty">Waiting for data...</div>;

  const stats = [
    { label: "Last", value: `$${Number(ticker.price).toLocaleString("en-US", { minimumFractionDigits: 2 })}`, cls: ticker.side === "buy" ? "green" : "red" },
    { label: "24h High", value: ticker.high_24h ? `$${Number(ticker.high_24h).toLocaleString()}` : "—" },
    { label: "24h Low", value: ticker.low_24h ? `$${Number(ticker.low_24h).toLocaleString()}` : "—" },
    { label: "24h Vol", value: ticker.volume_24h ? `${Number(ticker.volume_24h).toLocaleString(undefined, { maximumFractionDigits: 2 })} BTC` : "—" },
  ];

  return (
    <div className="ticker-bar">
      {stats.map((s) => (
        <div key={s.label} className="ticker-stat">
          <span className="ticker-label">{s.label}</span>
          <span className={`ticker-value ${s.cls || ""}`}>{s.value}</span>
        </div>
      ))}
    </div>
  );
}
