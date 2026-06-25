import { useMemo } from "react";
import { Search } from "lucide-react";
import { PageHeader, Section, Card, ModeBanner } from "../components/ui.jsx";
import { BarChartCard, LineChartCard } from "../components/charts.jsx";
import { formatNumber, formatPct } from "../lib/format.js";
import { HIGH_THRESHOLD } from "../lib/risk.js";

export default function FraudInsights({ data }) {
  const rows = data.scoredSample;

  const draining = useMemo(
    () =>
      rows
        .filter((r) => r.oldbalanceOrg > 0 && r.newbalanceOrig <= 1)
        .sort((a, b) => b.amount - a.amount)
        .slice(0, 40),
    [rows]
  );

  const topCustomers = useMemo(() => {
    const m = {};
    for (const r of rows) {
      const id = r.nameOrig;
      if (!m[id]) m[id] = { id, max: 0, txns: 0, total: 0 };
      m[id].max = Math.max(m[id].max, r.fraud_probability);
      m[id].txns += 1;
      m[id].total += Number(r.amount) || 0;
    }
    return Object.values(m).sort((a, b) => b.max - a.max).slice(0, 20);
  }, [rows]);

  return (
    <>
      <PageHeader icon={Search} title="Fraud Pattern Insights"
        subtitle="Where fraud concentrates: type, amount, time and balance behaviour" />
      <ModeBanner meta={data.meta} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <Section title="High-Risk Rate by Transaction Type">
            <BarChartCard data={data.byType} x="type" y="highRiskRatePct" color="#dc2626" label="High-risk %" />
          </Section>
        </Card>
        <Card>
          <Section title="High-Risk Rate by Amount Band">
            <BarChartCard data={data.byAmountBand} x="band" y="highRiskRatePct" color="#f59e0b" label="High-risk %" />
          </Section>
        </Card>
      </div>

      <div className="mt-4">
        <Card>
          <Section title="High-Risk Transactions Over Time">
            <LineChartCard data={data.byStep} x="step" y="highRisk" color="#dc2626" label="High-risk" height={260} />
          </Section>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <Section title={`Balance-Draining Transactions (${draining.length})`}>
            <div className="max-h-80 overflow-auto rounded-xl border border-navy-600/60">
              <table className="min-w-full">
                <thead className="sticky top-0 bg-navy-900/95">
                  <tr><th className="th">Customer</th><th className="th">Type</th><th className="th">Amount</th><th className="th">Old bal</th></tr>
                </thead>
                <tbody className="divide-y divide-navy-700/60">
                  {draining.map((r, i) => (
                    <tr key={i}>
                      <td className="td font-mono text-xs">{r.nameOrig}</td>
                      <td className="td">{r.type}</td>
                      <td className="td text-risk-high">{r.amount.toLocaleString()}</td>
                      <td className="td text-muted">{Number(r.oldbalanceOrg).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        </Card>

        <Card>
          <Section title="Top High-Risk Customers">
            <div className="max-h-80 overflow-auto rounded-xl border border-navy-600/60">
              <table className="min-w-full">
                <thead className="sticky top-0 bg-navy-900/95">
                  <tr><th className="th">Customer</th><th className="th">Max score</th><th className="th">Txns</th><th className="th">Total amt</th></tr>
                </thead>
                <tbody className="divide-y divide-navy-700/60">
                  {topCustomers.map((c) => (
                    <tr key={c.id}>
                      <td className="td font-mono text-xs">{c.id}</td>
                      <td className="td">
                        <span className={c.max >= HIGH_THRESHOLD ? "font-bold text-risk-high" : ""}>
                          {formatPct(c.max * 100, 0)}
                        </span>
                      </td>
                      <td className="td">{c.txns}</td>
                      <td className="td text-muted">{formatNumber(Math.round(c.total))}</td>
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
