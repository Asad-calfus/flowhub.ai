"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const SERIES_1 = "#2a78d6";

interface DistributionBarChartProps {
  data: Record<string, number>;
  color?: string;
  layout?: "horizontal" | "vertical";
}

export function DistributionBarChart({ data, color = SERIES_1, layout = "horizontal" }: DistributionBarChartProps) {
  const rows = Object.entries(data)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  if (rows.length === 0) return null;

  if (layout === "vertical") {
    return (
      <ResponsiveContainer width="100%" height={Math.max(180, rows.length * 32)}>
        <BarChart data={rows} layout="vertical" margin={{ left: 24 }}>
          <CartesianGrid stroke="#e1e0d9" horizontal={false} />
          <XAxis type="number" allowDecimals={false} stroke="#898781" fontSize={12} />
          <YAxis type="category" dataKey="name" width={140} stroke="#898781" fontSize={12} />
          <Tooltip />
          <Bar dataKey="value" fill={color} radius={[0, 4, 4, 0]} maxBarSize={22} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={rows} margin={{ bottom: 24 }}>
        <CartesianGrid stroke="#e1e0d9" vertical={false} />
        <XAxis dataKey="name" stroke="#898781" fontSize={11} angle={-20} textAnchor="end" interval={0} />
        <YAxis allowDecimals={false} stroke="#898781" fontSize={12} />
        <Tooltip />
        <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} maxBarSize={40} />
      </BarChart>
    </ResponsiveContainer>
  );
}
