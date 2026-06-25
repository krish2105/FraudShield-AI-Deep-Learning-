import {
  LayoutDashboard, Activity, AlertTriangle, DollarSign, Users, Gauge, Layers, ShieldAlert,
} from "lucide-react";
import { PageHeader, Section, Card, KpiCard, ModeBanner } from "../components/ui.jsx";
import { AreaChartCard, LineChartCard, BarChartCard } from "../components/charts.jsx";
import { formatNumber, formatCurrency, formatPct, probToPct } from "../lib/format.js";

export default function ExecutiveOverview({ data }) {
  const k = data.kpis;
  return (
    <>
      <PageHeader
        icon={LayoutDashboard}
        title="Executive Overview"
        subtitle="Portfolio-level view of payment fraud risk and exposure"
      />
      <ModeBanner meta={data.meta} />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Total Transactions" value={formatNumber(k.totalTransactions)}
                 sub="in current view" accent="#3b82f6" icon={Activity} />
        <KpiCard label="Flagged Fraud (label)" value={formatNumber(k.fraudTransactions)}
                 sub={`${formatPct(k.fraudPercentage, 2)} of volume`} accent="#dc2626" icon={AlertTriangle} />
        <KpiCard label="Total Transaction Value" value={formatCurrency(k.totalValue)}
                 sub="processed" accent="#0ea5e9" icon={DollarSign} />
        <KpiCard label="Estimated Amount at Risk" value={formatCurrency(k.amountAtRisk)}
                 sub="high-risk transactions" accent="#f59e0b" icon={ShieldAlert} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="High-Risk Transactions" value={formatNumber(k.highRiskTransactions)}
                 sub="score ≥ 0.71" accent="#dc2626" icon={AlertTriangle} />
        <KpiCard label="High-Risk Customers" value={formatNumber(k.highRiskCustomers)}
                 sub="need review" accent="#f59e0b" icon={Users} />
        <KpiCard label="Avg Fraud Score" value={probToPct(k.avgScore, 1)}
                 sub="portfolio mean" accent="#3b82f6" icon={Gauge} />
        <KpiCard label="Manual Review Rate" value={formatPct(k.reviewRate)}
                 sub="medium-risk band" accent="#8b5cf6" icon={Layers} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <Section title="High-Risk Transactions by Time Step">
            <AreaChartCard data={data.byStep} x="step" y="highRisk" color="#dc2626" label="High-risk" />
          </Section>
        </Card>
        <Card>
          <Section title="Transaction Volume by Time Step">
            <LineChartCard data={data.byStep} x="step" y="transactions" color="#38bdf8" label="Transactions" />
          </Section>
        </Card>
      </div>

      <div className="mt-4">
        <Card>
          <Section title="Top Fraud Transaction Types">
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <BarChartCard data={data.byType} x="type" y="fraud" color="#dc2626" label="Fraud count" height={300} />
              </div>
              <div className="overflow-auto">
                <table className="min-w-full">
                  <thead>
                    <tr>
                      <th className="th">Type</th><th className="th">Total</th>
                      <th className="th">Fraud</th><th className="th">Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-700/60">
                    {data.byType.map((t) => (
                      <tr key={t.type}>
                        <td className="td font-medium">{t.type}</td>
                        <td className="td">{formatNumber(t.total)}</td>
                        <td className="td text-risk-high">{t.fraud}</td>
                        <td className="td">{formatPct(t.fraudRatePct, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Section>
        </Card>
      </div>

      <p className="mt-4 text-center text-xs text-muted">
        FraudShield AI · scores blend sequence behaviour into a single risk number that maps
        directly to a business action.
      </p>
    </>
  );
}
