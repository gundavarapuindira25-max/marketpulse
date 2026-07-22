import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

/**
 * DepthChart — cumulative order book liquidity by price (market depth)
 */
export default function DepthChart({ bids, asks }) {
  if (!bids?.length || !asks?.length) {
    return <div className="chart-empty">Waiting for order book...</div>;
  }

  let cum = 0;
  const bidPoints = [...bids]
    .sort((a, b) => b.price - a.price)
    .map((b) => {
      cum += b.size;
      return { price: b.price, bidDepth: parseFloat(cum.toFixed(4)) };
    })
    .reverse();

  cum = 0;
  const askPoints = [...asks]
    .sort((a, b) => a.price - b.price)
    .map((a) => {
      cum += a.size;
      return { price: a.price, askDepth: parseFloat(cum.toFixed(4)) };
    });

  const data = [...bidPoints, ...askPoints];

  return (
    <div className="chart-fill">
      <div className="chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="price"
              tickFormatter={(v) => `$${Math.round(v).toLocaleString()}`}
              tick={{ fill: "#7a8a9a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v) => v.toFixed(1)}
              tick={{ fill: "#7a8a9a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            <Tooltip
              formatter={(value, name) => [
                `${Number(value).toFixed(4)} BTC`,
                name === "bidDepth" ? "Bid depth" : "Ask depth",
              ]}
              labelFormatter={(v) => `$${Number(v).toLocaleString()}`}
              contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 4, fontSize: 11 }}
            />
            <Area
              type="stepAfter"
              dataKey="bidDepth"
              stroke="#00c896"
              fill="#00c896"
              fillOpacity={0.15}
              dot={false}
              isAnimationActive={false}
            />
            <Area
              type="stepBefore"
              dataKey="askDepth"
              stroke="#ff4d4f"
              fill="#ff4d4f"
              fillOpacity={0.15}
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
