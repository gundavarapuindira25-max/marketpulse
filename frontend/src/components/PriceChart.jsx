import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

/**
 * PriceChart — live tick price chart with a simple moving average overlay
 */

function sma(data, window = 20) {
  return data.map((d, i) => {
    if (i < window - 1) return { ...d, sma: null };
    const slice = data.slice(i - window + 1, i + 1);
    const avg = slice.reduce((sum, x) => sum + x.price, 0) / window;
    return { ...d, sma: parseFloat(avg.toFixed(2)) };
  });
}

// VWAP needs per-tick volume, which the ticker feed doesn't provide directly —
// we approximate it from the delta in cumulative 24h volume between ticks.
function vwap(data) {
  let cumPV = 0;
  let cumV = 0;
  return data.map((d) => {
    const vol = d.size || 0;
    cumPV += d.price * vol;
    cumV += vol;
    return { ...d, vwap: cumV > 0 ? parseFloat((cumPV / cumV).toFixed(2)) : null };
  });
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="chart-tooltip">
      <div className="ct-price">${d?.price?.toLocaleString("en-US", { minimumFractionDigits: 2 })}</div>
      {d?.sma && <div className="ct-sma">SMA20: ${d.sma.toLocaleString()}</div>}
      {d?.vwap && <div className="ct-vwap">VWAP: ${d.vwap.toLocaleString()}</div>}
    </div>
  );
};

export default function PriceChart({ ticks }) {
  const data = vwap(sma(ticks));
  const prices = ticks.map((t) => t.price);
  const minP = Math.min(...prices) * 0.9999;
  const maxP = Math.max(...prices) * 1.0001;

  if (ticks.length < 2) {
    return <div className="chart-empty">Collecting data...</div>;
  }

  return (
    <div className="chart-fill">
      <div className="chart-legend">
        <span className="legend-item"><i className="legend-dot price" />Price</span>
        <span className="legend-item"><i className="legend-dot sma" />SMA20</span>
        <span className="legend-item"><i className="legend-dot vwap" />VWAP</span>
      </div>
      <div className="chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00c896" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#00c896" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="time" hide />
            <YAxis
              domain={[minP, maxP]}
              tickFormatter={(v) => `$${v.toLocaleString()}`}
              width={90}
              tick={{ fill: "#7a8a9a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="price"
              stroke="#00c896"
              strokeWidth={1.5}
              fill="url(#priceGrad)"
              dot={false}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="sma"
              stroke="#f0a500"
              strokeWidth={1}
              fill="none"
              dot={false}
              strokeDasharray="4 2"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="vwap"
              stroke="#58a6ff"
              strokeWidth={1.2}
              fill="none"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
