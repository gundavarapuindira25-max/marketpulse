import { ComposedChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

/**
 * CandleChart — 1-minute OHLCV candlestick chart
 */

const UP = "#00c896";
const DOWN = "#ff4d4f";

function CandleShape(props) {
  const { x, y, width, height, payload } = props;
  const { open, close, high, low } = payload;
  const isUp = close >= open;
  const color = isUp ? UP : DOWN;

  const yFor = (v) => {
    if (high === low) return y + height / 2;
    return y + ((high - v) / (high - low)) * height;
  };

  const bodyTop = yFor(Math.max(open, close));
  const bodyBottom = yFor(Math.min(open, close));
  const bodyHeight = Math.max(1, bodyBottom - bodyTop);
  const wickX = x + width / 2;

  return (
    <g>
      <line x1={wickX} x2={wickX} y1={y} y2={y + height} stroke={color} strokeWidth={1} />
      <rect x={x} y={bodyTop} width={width} height={bodyHeight} fill={color} />
    </g>
  );
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  const fmt = (v) => Number(v).toLocaleString("en-US", { minimumFractionDigits: 2 });
  return (
    <div className="chart-tooltip">
      <div>{new Date(d.ts * 1000).toLocaleTimeString()}</div>
      <div>O: {fmt(d.open)}</div>
      <div>H: {fmt(d.high)}</div>
      <div>L: {fmt(d.low)}</div>
      <div className={d.close >= d.open ? "ct-price" : "ct-vwap"}>C: {fmt(d.close)}</div>
    </div>
  );
};

export default function CandleChart({ candles }) {
  if (candles.length < 2) {
    return <div className="chart-empty">Collecting candles...</div>;
  }

  const data = candles.map((c) => ({ ...c, range: [c.low, c.high] }));
  const lows = candles.map((c) => c.low);
  const highs = candles.map((c) => c.high);
  const minP = Math.min(...lows) * 0.999;
  const maxP = Math.max(...highs) * 1.001;

  return (
    <div className="chart-fill">
      <div className="chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="ts"
              tickFormatter={(ts) => new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              tick={{ fill: "#7a8a9a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              minTickGap={40}
            />
            <YAxis
              domain={[minP, maxP]}
              tickFormatter={(v) => `$${v.toLocaleString()}`}
              width={90}
              tick={{ fill: "#7a8a9a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="range" shape={<CandleShape />} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
