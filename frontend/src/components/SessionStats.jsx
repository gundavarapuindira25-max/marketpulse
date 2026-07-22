/**
 * SessionStats — summary tiles for the current browser session
 */
export default function SessionStats({ stats, ticker }) {
  const elapsedSec = Math.max(0, Math.floor((Date.now() - stats.startTime) / 1000));
  const mins = Math.floor(elapsedSec / 60);
  const secs = elapsedSec % 60;

  const items = [
    { label: "Session Duration", value: `${mins}m ${secs}s` },
    { label: "Trades Seen", value: stats.tradeCount.toLocaleString() },
    { label: "Current Price", value: ticker?.price ? `$${Number(ticker.price).toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "—" },
    { label: "Session Low", value: stats.minPrice ? `$${stats.minPrice.toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "—" },
    { label: "Session High", value: stats.maxPrice ? `$${stats.maxPrice.toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "—" },
    { label: "24h Volume", value: ticker?.volume_24h ? `${Number(ticker.volume_24h).toLocaleString(undefined, { maximumFractionDigits: 2 })} BTC` : "—" },
  ];

  return (
    <div className="stats-grid">
      {items.map((it) => (
        <div key={it.label} className="stat-tile">
          <span className="stat-label">{it.label}</span>
          <span className="stat-value">{it.value}</span>
        </div>
      ))}
    </div>
  );
}
