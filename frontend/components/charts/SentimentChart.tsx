"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

// Validated for CVD/normal-vision separation via the dataviz skill's
// scripts/validate_palette.js (categorical, light mode) - do not tweak
// individual hexes without re-running it.
const SENTIMENT_COLORS: Record<string, string> = {
  Positive: "#008300",
  Neutral: "#2a78d6",
  Negative: "#e34948",
  Mixed: "#4a3aa7",
};

interface SentimentChartProps {
  distribution: Record<string, number>;
}

export function SentimentChart({ distribution }: SentimentChartProps) {
  const data = Object.entries(distribution)
    .filter(([, value]) => value > 0)
    .map(([name, value]) => ({ name, value }));

  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
          {data.map((entry) => (
            <Cell key={entry.name} fill={SENTIMENT_COLORS[entry.name] || "#898781"} />
          ))}
        </Pie>
        <Tooltip formatter={(value: number) => `${(value * 100).toFixed(0)}%`} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
