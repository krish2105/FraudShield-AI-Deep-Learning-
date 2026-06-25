import { useMemo, useState } from "react";
import Papa from "papaparse";
import { Bell, Download } from "lucide-react";
import { PageHeader, Section, Card, KpiCard, RiskBadge, ModeBanner } from "../components/ui.jsx";
import { formatNumber, formatCurrency } from "../lib/format.js";

export default function AlertCenter({ data }) {
  const [thr, setThr] = useState(data.meta.highThreshold ?? 0.7);
  const rows = data.scoredSample;

  const alerts = useMemo(
    () =>
      rows
        .filter((r) => r.fraud_probability >= thr)
        .sort((a, b) => b.fraud_probability - a.fraud_probability)
        .map((r) => ({ ...r, status: "OPEN" })),
    [rows, thr]
  );

  const amount = alerts.reduce((a, b) => a + (Number(b.amount) || 0), 0);
  const customers = new Set(alerts.map((a) => a.nameOrig)).size;

  function downloadCsv() {
    const out = alerts.map((a) => ({
      customer_id: a.nameOrig, type: a.type, amount: a.amount,
      fraud_probability: a.fraud_probability, risk_label: a.risk_label,
      recommended_action: a.recommended_action, status: a.status,
    }));
    const csv = Papa.unparse(out);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "fraudshield_alert_report.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <PageHeader icon={Bell} title="Alert Center"
        subtitle="Operational queue of high-risk transactions for the fraud team" />
      <ModeBanner meta={data.meta} />

      <Card>
        <Section title="Alert Threshold">
          <div className="flex items-center gap-4">
            <input type="range" min="0.3" max="0.95" step="0.01" value={thr}
                   onChange={(e) => setThr(Number(e.target.value))}
                   className="h-2 w-full max-w-md accent-accent" />
            <span className="pill bg-navy-700 text-ink">score ≥ {thr.toFixed(2)}</span>
          </div>
        </Section>
      </Card>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <KpiCard label="Open Alerts" value={formatNumber(alerts.length)} sub={`score ≥ ${thr.toFixed(2)}`} accent="#dc2626" />
        <KpiCard label="Amount in Alerts" value={formatCurrency(amount)} sub="total exposure" accent="#f59e0b" />
        <KpiCard label="Customers Involved" value={formatNumber(customers)} sub="unique senders" accent="#3b82f6" />
      </div>

      <div className="mt-4">
        <Card>
          <Section title="High-Risk Alert Queue"
            right={<button className="btn" onClick={downloadCsv}><Download size={16} /> Export report</button>}>
            <div className="max-h-[460px] overflow-auto rounded-xl border border-navy-600/60">
              <table className="min-w-full">
                <thead className="sticky top-0 bg-navy-900/95">
                  <tr>
                    <th className="th">Customer</th><th className="th">Type</th><th className="th">Amount</th>
                    <th className="th">Risk</th><th className="th">Action</th><th className="th">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-700/60">
                  {alerts.map((a, i) => (
                    <tr key={i} className="hover:bg-navy-700/40">
                      <td className="td font-mono text-xs">{a.nameOrig}</td>
                      <td className="td">{a.type}</td>
                      <td className="td">{Number(a.amount).toLocaleString()}</td>
                      <td className="td"><RiskBadge probability={a.fraud_probability} /></td>
                      <td className="td text-muted">{a.recommended_action}</td>
                      <td className="td"><span className="pill bg-risk-high/20 text-red-200">{a.status}</span></td>
                    </tr>
                  ))}
                  {!alerts.length && (
                    <tr><td className="td text-muted" colSpan={6}>No alerts at this threshold.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Section>
        </Card>
      </div>
    </>
  );
}
