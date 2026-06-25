import { useState } from "react";
import { PiggyBank } from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";
import { PageHeader, Section, Card, KpiCard } from "../components/ui.jsx";
import { formatCurrency, formatPct } from "../lib/format.js";

export default function BusinessImpact({ data }) {
  const nHigh = data.kpis.highRiskTransactions;
  const nMedium = Math.round((data.kpis.reviewRate / 100) * data.kpis.totalTransactions);

  const [avgLoss, setAvgLoss] = useState(1200);
  const [reviewCost, setReviewCost] = useState(8);
  const [caught, setCaught] = useState(nHigh);
  const [falseRate, setFalseRate] = useState(25);

  const trueFrauds = caught * (1 - falseRate / 100);
  const lossPrevented = trueFrauds * avgLoss;
  const reviewCases = caught + nMedium;
  const totalReviewCost = reviewCases * reviewCost;
  const net = lossPrevented - totalReviewCost;
  const workload = (100 * reviewCases) / Math.max(data.kpis.totalTransactions, 1);

  const waterfall = [
    { name: "Loss prevented", value: Math.round(lossPrevented), color: "#16a34a" },
    { name: "Review cost", value: -Math.round(totalReviewCost), color: "#dc2626" },
    { name: "Net savings", value: Math.round(net), color: "#2563eb" },
  ];

  return (
    <>
      <PageHeader icon={PiggyBank} title="Business Impact Simulator"
        subtitle="Estimate fraud loss prevented, review cost and net savings" />

      <Card>
        <Section title="Your Assumptions">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Field label="Avg fraud loss per case ($)" value={avgLoss} set={setAvgLoss} step={100} />
            <Field label="Manual review cost per case ($)" value={reviewCost} set={setReviewCost} step={1} />
            <Field label="Fraud cases caught (high-risk)" value={caught} set={setCaught} step={1} />
            <div className="text-sm">
              <span className="mb-1 block text-muted">Estimated false-alert rate: {falseRate}%</span>
              <input type="range" min="0" max="80" value={falseRate}
                     onChange={(e) => setFalseRate(Number(e.target.value))}
                     className="mt-3 h-2 w-full accent-accent" />
            </div>
          </div>
        </Section>
      </Card>

      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Fraud Loss Prevented" value={formatCurrency(lossPrevented)}
                 sub={`~${Math.round(trueFrauds)} true frauds`} accent="#16a34a" />
        <KpiCard label="Manual Review Cost" value={formatCurrency(totalReviewCost)}
                 sub={`${reviewCases.toLocaleString()} cases reviewed`} accent="#f59e0b" />
        <KpiCard label="Net Savings" value={formatCurrency(net)}
                 sub="prevented − review cost" accent="#2563eb" />
        <KpiCard label="Review Workload" value={formatPct(workload)}
                 sub="of all transactions" accent="#8b5cf6" />
      </div>

      <div className="mt-4">
        <Card>
          <Section title="From Fraud Prevented to Net Savings">
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={waterfall} margin={{ top: 10, right: 16, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#16223f" vertical={false} />
                <XAxis dataKey="name" stroke="#3b4a6b" tick={{ fill: "#8aa0c2", fontSize: 12 }} />
                <YAxis stroke="#3b4a6b" tick={{ fill: "#8aa0c2", fontSize: 11 }} />
                <Tooltip formatter={(v) => formatCurrency(v)} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {waterfall.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p className="mt-2 text-xs text-muted">
              Illustrative figures based on your assumptions. Replace with your bank's real numbers
              for a board-ready estimate.
            </p>
          </Section>
        </Card>
      </div>
    </>
  );
}

function Field({ label, value, set, step }) {
  return (
    <label className="text-sm">
      <span className="mb-1 block text-muted">{label}</span>
      <input type="number" step={step} value={value} min={0}
             onChange={(e) => set(Number(e.target.value))} className="input w-full" />
    </label>
  );
}
