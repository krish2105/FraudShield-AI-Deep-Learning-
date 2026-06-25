import { useMemo, useState } from "react";
import { Database } from "lucide-react";
import { PageHeader, Section, Card, ModeBanner } from "../components/ui.jsx";
import { BarChartCard, DonutChartCard } from "../components/charts.jsx";
import { formatNumber } from "../lib/format.js";

export default function DatasetExplorer({ data }) {
  const rows = data.scoredSample;
  const types = useMemo(
    () => Array.from(new Set(rows.map((r) => r.type))).sort(),
    [rows]
  );
  const [selType, setSelType] = useState("ALL");
  const [fraudFilter, setFraudFilter] = useState("All");

  const filtered = useMemo(() => {
    return rows.filter((r) => {
      if (selType !== "ALL" && r.type !== selType) return false;
      if (fraudFilter === "Fraud only" && r.isFraud !== 1) return false;
      if (fraudFilter === "Non-fraud only" && r.isFraud === 1) return false;
      return true;
    });
  }, [rows, selType, fraudFilter]);

  const fraudVs = [
    { name: "Genuine", value: data.fraudVsGenuine.genuine },
    { name: "Fraud", value: data.fraudVsGenuine.fraud },
  ];

  const cols = ["step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig", "isFraud"];

  return (
    <>
      <PageHeader icon={Database} title="Dataset Explorer"
        subtitle="Preview, quality checks and distributions of the transaction data" />
      <ModeBanner meta={{ source: data.meta.source }} />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Rows (full)" value={formatNumber(data.kpis.totalTransactions)} />
        <Stat label="Columns" value={data.columns.length} />
        <Stat label="Missing values"
              value={formatNumber(data.missingByColumn.reduce((a, b) => a + b.missing, 0))} />
        <Stat label="Sample rows shown" value={formatNumber(rows.length)} />
      </div>

      <div className="mt-6">
        <Card>
          <Section title="Filters">
            <div className="flex flex-wrap gap-4">
              <label className="text-sm">
                <span className="mb-1 block text-muted">Transaction type</span>
                <select className="input" value={selType} onChange={(e) => setSelType(e.target.value)}>
                  <option value="ALL">All types</option>
                  {types.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </label>
              <label className="text-sm">
                <span className="mb-1 block text-muted">Fraud label</span>
                <select className="input" value={fraudFilter} onChange={(e) => setFraudFilter(e.target.value)}>
                  <option>All</option><option>Fraud only</option><option>Non-fraud only</option>
                </select>
              </label>
            </div>
          </Section>

          <Section title="Data Preview">
            <div className="max-h-80 overflow-auto rounded-xl border border-navy-600/60">
              <table className="min-w-full">
                <thead className="sticky top-0 bg-navy-900/95">
                  <tr>{cols.map((c) => <th key={c} className="th">{c}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-navy-700/60">
                  {filtered.slice(0, 200).map((r, i) => (
                    <tr key={i} className="hover:bg-navy-700/40">
                      {cols.map((c) => (
                        <td key={c} className="td">
                          {c === "isFraud"
                            ? (r[c] === 1 ? <span className="text-risk-high font-semibold">1</span> : "0")
                            : typeof r[c] === "number" ? r[c].toLocaleString() : r[c]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-xs text-muted">
              Showing first 200 of {formatNumber(filtered.length)} filtered sample rows.
            </p>
          </Section>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <Section title="Fraud vs Genuine (full data)">
            <DonutChartCard data={fraudVs} colors={["#2563eb", "#dc2626"]} />
          </Section>
        </Card>
        <Card>
          <Section title="Transaction Type Distribution">
            <BarChartCard data={data.byType} x="type" y="total" color="#3b82f6" label="Count" />
          </Section>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <Section title="Amount Distribution (99th pct capped)">
            <BarChartCard data={data.amountHistogram} x="x" y="count" color="#38bdf8" label="Count" />
          </Section>
        </Card>
        <Card>
          <Section title="Column Descriptions">
            <div className="max-h-72 overflow-auto rounded-xl border border-navy-600/60">
              <table className="min-w-full">
                <thead className="sticky top-0 bg-navy-900/95">
                  <tr><th className="th">Column</th><th className="th">Description</th></tr>
                </thead>
                <tbody className="divide-y divide-navy-700/60">
                  {data.columns.map((c) => (
                    <tr key={c.column}>
                      <td className="td font-mono text-accent-cyan">{c.column}</td>
                      <td className="td whitespace-normal text-muted">{c.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        </Card>
      </div>
    </>
  );
}

function Stat({ label, value }) {
  return (
    <Card className="!p-4">
      <div className="text-[11px] uppercase tracking-wider text-muted">{label}</div>
      <div className="mt-1 text-xl font-bold text-white">{value}</div>
    </Card>
  );
}
