import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

/**
 * SpreadChart — bid/ask spread over time
 */
export default function SpreadChart({ spreads }) {
  if (spreads.length < 2) {
    return <div className="chart-empty">Collecting data...</div>;
  }

  return (
    <div className="chart-fill">
      <div className="chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={spreads} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <XAxis dataKey="time" hide />
            <YAxis
              tickFormatter={(v) => `$${v.toFixed(2)}`}
              tick={{ fill: "#7a8a9a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={70}
            />
            <Tooltip
              formatter={(v) => [`$${Number(v).toFixed(2)}`, "Spread"]}
              labelFormatter={() => ""}
              contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 4, fontSize: 11 }}
            />
            <Line
              type="monotone"
              dataKey="spread"
              stroke="#f0a500"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
