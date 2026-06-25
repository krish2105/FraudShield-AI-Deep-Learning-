import { useMemo, useState } from "react";
import { GitBranch, TrendingUp, Droplet, Siren, CheckCircle2 } from "lucide-react";
import {
  ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import { PageHeader, Section, Card, RiskBadge, Banner } from "../components/ui.jsx";
import { HIGH_THRESHOLD } from "../lib/risk.js";

export default function SequenceAnalyzer({ data }) {
  const customers = data.customers;
  const ids = useMemo(() => Object.keys(customers), [customers]);
  // default to the most risky customer
  const defaultId = useMemo(() => {
    let best = ids[0], bestP = -1;
    for (const id of ids) {
      const m = Math.max(...customers[id].map((t) => t.fraud_probability));
      if (m > bestP) { bestP = m; best = id; }
    }
    return best;
  }, [ids, customers]);

  const [cid, setCid] = useState(defaultId);
  const seq = customers[cid] || [];
  const last = seq.slice(-(data.meta.sequenceLength + 1));
  const maxP = last.length ? Math.max(...seq.map((t) => t.fraud_probability)) : 0;

  const chart = last.map((t, i) => ({
    n: i + 1,
    amount: t.amount,
    before: t.oldbalanceOrg,
    after: t.newbalanceOrig,
  }));

  const drained = last.some((t) => t.oldbalanceOrg > 0 && t.newbalanceOrig <= 1);
  const amounts = last.map((t) => t.amount).sort((a, b) => a - b);
  const median = amounts.length ? amounts[Math.floor(amounts.length / 2)] : 0;
  const bigJump = Math.max(...last.map((t) => t.amount), 0) > 5 * (median + 1);

  const notes = [];
  if (bigJump) notes.push({ icon: TrendingUp, text: "A sudden large jump in transaction amount vs this customer's normal behaviour." });
  if (drained) notes.push({ icon: Droplet, text: "At least one transaction drains the sender's balance to near zero — a classic fraud signal." });
  if (maxP >= HIGH_THRESHOLD) notes.push({ icon: Siren, text: "The most recent behaviour scores High Risk and would be blocked / escalated." });
  if (!notes.length) notes.push({ icon: CheckCircle2, text: "Behaviour looks stable and consistent — small, regular amounts with healthy balances." });

  return (
    <>
      <PageHeader icon={GitBranch} title="Customer Sequence Analyzer"
        subtitle="How the LSTM reads a customer's recent behaviour as a sequence" />

      <Card>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <label className="text-sm">
            <span className="mb-1 block text-muted">🔎 Select a customer ID</span>
            <select className="input min-w-[220px]" value={cid} onChange={(e) => setCid(e.target.value)}>
              {ids.map((id) => <option key={id} value={id}>{id}</option>)}
            </select>
          </label>
          <div className="flex items-center gap-6">
            <Metric label="Transactions" value={seq.length} />
            <Metric label="Max fraud score" value={`${Math.round(maxP * 100)}%`} />
            <div>
              <div className="mb-1 text-[11px] uppercase tracking-wider text-muted">Current risk</div>
              <RiskBadge probability={maxP} />
            </div>
          </div>
        </div>
      </Card>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <Section title="Behaviour Timeline">
            <ResponsiveContainer width="100%" height={340}>
              <ComposedChart data={chart} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#16223f" vertical={false} />
                <XAxis dataKey="n" stroke="#3b4a6b" tick={{ fill: "#8aa0c2", fontSize: 11 }} />
                <YAxis stroke="#3b4a6b" tick={{ fill: "#8aa0c2", fontSize: 11 }} />
                <Tooltip />
                <Legend wrapperStyle={{ color: "#8aa0c2", fontSize: 12 }} />
                <Bar dataKey="amount" name="Amount" fill="#3b82f6" radius={[5, 5, 0, 0]} />
                <Line type="monotone" dataKey="before" name="Balance before" stroke="#38bdf8" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="after" name="Balance after" stroke="#dc2626" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </Section>
        </Card>

        <Card className="xl:col-span-2">
          <Section title={`Last ${last.length} Transactions`}>
            <div className="max-h-[300px] overflow-auto rounded-xl border border-navy-600/60">
              <table className="min-w-full">
                <thead className="sticky top-0 bg-navy-900/95">
                  <tr><th className="th">Step</th><th className="th">Type</th><th className="th">Amount</th><th className="th">Risk</th></tr>
                </thead>
                <tbody className="divide-y divide-navy-700/60">
                  {last.map((t, i) => (
                    <tr key={i}>
                      <td className="td">{t.step}</td>
                      <td className="td">{t.type}</td>
                      <td className="td">{t.amount.toLocaleString()}</td>
                      <td className="td">{Math.round(t.fraud_probability * 100)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        </Card>
      </div>

      <div className="mt-4">
        <Card>
          <Section title="Why the Sequence Matters">
            <ul className="space-y-2">
              {notes.map((n, i) => (
                <li key={i} className="flex items-start gap-3 text-sm">
                  <n.icon size={18} className="mt-0.5 text-accent-cyan" />
                  <span>{n.text}</span>
                </li>
              ))}
            </ul>
            <Banner tone="info" title="How the LSTM uses sequence memory:">
              A normal model looks at one transaction alone. The LSTM reads the last{" "}
              {data.meta.sequenceLength} transactions in order and remembers the pattern. So a
              payment of 9,000 looks fine on its own, but right after a history of 100 → 120 → 90 it
              stands out as suspicious.
            </Banner>
          </Section>
        </Card>
      </div>
    </>
  );
}

function Metric({ label, value }) {
  return (
    <div>
      <div className="mb-1 text-[11px] uppercase tracking-wider text-muted">{label}</div>
      <div className="text-xl font-bold text-white">{value}</div>
    </div>
  );
}
