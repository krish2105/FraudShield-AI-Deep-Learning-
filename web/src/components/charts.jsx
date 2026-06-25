// Thin wrappers around recharts with the FraudShield dark theme baked in.
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";

const AXIS = { stroke: "#3b4a6b", tick: { fill: "#8aa0c2", fontSize: 11 } };
const GRID = "#16223f";

export function BarChartCard({ data, x, y, color = "#3b82f6", height = 300, label }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey={x} {...AXIS} />
        <YAxis {...AXIS} />
        <Tooltip cursor={{ fill: "rgba(56,189,248,0.06)" }} />
        <Bar dataKey={y} name={label || y} fill={color} radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function LineChartCard({ data, x, y, color = "#38bdf8", height = 300, label }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey={x} {...AXIS} />
        <YAxis {...AXIS} />
        <Tooltip />
        <Line type="monotone" dataKey={y} name={label || y} stroke={color}
              strokeWidth={2.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function AreaChartCard({ data, x, y, color = "#dc2626", height = 300, label }) {
  const id = `grad-${y}`;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.5} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey={x} {...AXIS} />
        <YAxis {...AXIS} />
        <Tooltip />
        <Area type="monotone" dataKey={y} name={label || y} stroke={color}
              strokeWidth={2} fill={`url(#${id})`} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function HBarChartCard({ data, x, y, color = "#3b82f6", height = 360, label }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 6, right: 24, left: 20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} horizontal={false} />
        <XAxis type="number" {...AXIS} />
        <YAxis type="category" dataKey={y} width={150} {...AXIS} />
        <Tooltip cursor={{ fill: "rgba(56,189,248,0.06)" }} />
        <Bar dataKey={x} name={label || x} fill={color} radius={[0, 6, 6, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DonutChartCard({ data, height = 300, colors = ["#2563eb", "#dc2626"] }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="80%"
             paddingAngle={3}>
          {data.map((_, i) => (
            <Cell key={i} fill={colors[i % colors.length]} stroke="none" />
          ))}
        </Pie>
        <Tooltip />
        <Legend wrapperStyle={{ color: "#8aa0c2", fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
