/**
 * OrderBook — displays top 20 bids and asks with depth bars
 */
export default function OrderBook({ bids, asks, midPrice }) {
  const maxSize = Math.max(
    ...bids.map((b) => b.size),
    ...asks.map((a) => a.size),
    0.0001
  );

  return (
    <div className="order-book">
      {/* Asks — lowest ask at bottom, so reverse */}
      <div className="book-side asks">
        <div className="book-header">
          <span>Price (USD)</span>
          <span>Size (BTC)</span>
          <span>Total</span>
        </div>
        {[...asks].reverse().map((row, i) => {
          const pct = Math.min((row.size / maxSize) * 100, 100);
          return (
            <div key={i} className="book-row ask-row">
              <div className="depth-bar ask-bar" style={{ width: `${pct}%` }} />
              <span className="price ask-price">{Number(row.price).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
              <span className="size">{row.size.toFixed(5)}</span>
              <span className="total">{(row.price * row.size).toFixed(2)}</span>
            </div>
          );
        })}
      </div>

      {/* Mid price */}
      {midPrice && (
        <div className="mid-price">
          <span>Mid</span>
          <span className="mid-value">${midPrice.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
        </div>
      )}

      {/* Bids */}
      <div className="book-side bids">
        {bids.map((row, i) => {
          const pct = Math.min((row.size / maxSize) * 100, 100);
          return (
            <div key={i} className="book-row bid-row">
              <div className="depth-bar bid-bar" style={{ width: `${pct}%` }} />
              <span className="price bid-price">{Number(row.price).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
              <span className="size">{row.size.toFixed(5)}</span>
              <span className="total">{(row.price * row.size).toFixed(2)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
