import { useMemo, useState } from "react";
import { Lightbulb } from "lucide-react";
import { PageHeader, Section, Card, RiskBadge, Banner } from "../components/ui.jsx";
import { HBarChartCard } from "../components/charts.jsx";
import { explainRow, riskBand } from "../lib/risk.js";

export default function Explainability({ data }) {
  const top = useMemo(
    () => [...data.scoredSample].sort((a, b) => b.fraud_probability - a.fraud_probability).slice(0, 200),
    [data.scoredSample]
  );
  const [idx, setIdx] = useState(0);
  const row = top[idx] || {};
  const reasons = explainRow(row);
  const band = riskBand(row.fraud_probability);

  // feature importance rounded for the chart
  const importance = data.featureImportance.map((f) => ({
    feature: f.feature,
    importance: Number((f.importance).toFixed(3)),
  }));

  return (
    <>
      <PageHeader icon={Lightbulb} title="Explainability Panel"
        subtitle="Plain-English reasons a transaction is risky (no black box)" />

      <Card>
        <Section title="Which Signals Drive Risk? (approximate importance)">
          <p className="mb-3 text-xs text-muted">
            SHAP-style values need the trained model. As a transparent approximation we show how
            strongly each engineered feature moves together with the fraud score (|correlation|).
          </p>
          <HBarChartCard data={importance} x="importance" y="feature" color="#3b82f6" height={420} label="|corr|" />
        </Section>
      </Card>

      <div className="mt-4">
        <Card>
          <Section title="Explain a Single Transaction">
            <label className="text-sm">
              <span className="mb-1 block text-muted">Pick a transaction (sorted by risk)</span>
              <select className="input w-full max-w-xl" value={idx} onChange={(e) => setIdx(Number(e.target.value))}>
                {top.map((r, i) => (
                  <option key={i} value={i}>
                    {r.type} · {Number(r.amount).toLocaleString()} · score {Math.round(r.fraud_probability * 100)}%
                  </option>
                ))}
              </select>
            </label>

            <div className="mt-4 flex items-center gap-3">
              <span className="text-sm text-muted">Risk:</span>
              <RiskBadge probability={row.fraud_probability} />
            </div>

            {reasons.length ? (
              <div className="mt-3">
                <p className="text-sm font-semibold">
                  This transaction is {band.label.toLowerCase()} because:
                </p>
                <ul className="mt-2 space-y-1.5 text-sm text-ink/90">
                  {reasons.map((r, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="mt-2 h-1.5 w-1.5 rounded-full bg-accent-cyan" />
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted">
                This transaction shows no strong fraud signals — small amount relative to balance,
                healthy remaining balance.
              </p>
            )}

            <Banner tone="info" title="Example explanation:">
              “This transaction is high risk because the amount is large compared to the old balance
              and the sender balance becomes zero.” Human-readable reasons keep an analyst in control.
            </Banner>
          </Section>
        </Card>
      </div>
    </>
  );
}
