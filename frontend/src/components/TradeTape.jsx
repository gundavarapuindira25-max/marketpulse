/**
 * TradeTape — scrolling feed of recent trades with buy/sell direction
 */
export default function TradeTape({ trades }) {
  if (!trades.length) {
    return <div className="chart-empty">Waiting for trades...</div>;
  }

  return (
    <div className="trade-tape">
      <div className="tape-header">
        <span>Time</span>
        <span>Price</span>
        <span>Side</span>
      </div>
      <div className="tape-rows">
        {trades.map((t) => {
          const isBuy = t.side?.toLowerCase() === "buy";
          return (
            <div key={t.id} className={`tape-row ${isBuy ? "buy" : "sell"}`}>
              <span className="tape-time">{new Date(t.time * 1000).toLocaleTimeString()}</span>
              <span className="tape-price">
                {Number(t.price).toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </span>
              <span className="tape-side">{isBuy ? "▲ BUY" : "▼ SELL"}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
