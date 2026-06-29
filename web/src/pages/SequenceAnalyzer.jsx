import { useMemo, useState } from "react";
import { GitBranch, TrendingUp, Droplet, Siren, CheckCircle2, BrainCircuit, ArrowRight, Cpu, Database, Wrench, Layers, Gauge, MonitorSmartphone } from "lucide-react";
import {
  ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import { PageHeader, Section, Card, RiskBadge, Banner } from "../components/ui.jsx";
import { HIGH_THRESHOLD, riskBand } from "../lib/risk.js";

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
          <Section title="How the LSTM Reads This Sequence (step by step)"
            right={<span className="pill bg-accent/15 text-accent-cyan"><BrainCircuit size={12} /> LSTM / RNN</span>}>
            <p className="mb-4 text-sm text-muted">
              The {last.length} transactions below are fed into the LSTM <b>one at a time, in time
              order</b>. At each step the network updates a hidden <b>memory cell</b> that carries
              the context forward. After the last transaction, that memory is turned into a single
              fraud score.
            </p>
            <LstmFlow steps={last} finalP={maxP} />
          </Section>
        </Card>
      </div>

      <div className="mt-4">
        <Card>
          <Section title="Interactive Explainer — From Labelled Data to a Live Score"
            right={<span className="pill bg-accent/15 text-accent-cyan"><BrainCircuit size={12} /> click each step</span>}>
            <PipelineExplainer meta={data.meta} customer={cid} seqLen={seq.length}
                               finalP={maxP} kpis={data.kpis} />
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
      <div className="text-xl font-bold text-ink">{value}</div>
    </div>
  );
}

// Interactive, clickable walkthrough of the whole pipeline, grounded in the
// currently-selected customer's REAL data. Answers three teacher questions:
// how data is injected, how the labelled table becomes sequences, why LSTM/RNN.
function PipelineExplainer({ meta, customer, seqLen, finalP, kpis }) {
  const [step, setStep] = useState(0);
  const nFeat = meta?.nFeatures ?? 14;
  const L = meta?.sequenceLength ?? 10;

  const STEPS = [
    {
      key: "inject", icon: Database, title: "1 · Data injected",
      color: "#0ea5e9",
      body: (
        <>
          <p className="text-sm">
            The raw <b>PaySim</b> file <code>data/paysim.csv</code> is loaded by the backend
            (<code>data_loader.py</code>). It is a <b>labelled</b> dataset — every row already carries
            an <code>isFraud</code> column (0 = genuine, 1 = fraud). That label is the answer the
            model learns to predict.
          </p>
          <ul className="mt-2 space-y-1 text-sm text-muted">
            <li>• Source now: <b>{meta?.source === "real" ? "real PaySim" : "sample"}</b> · {kpis?.totalTransactions?.toLocaleString()} rows · {kpis?.fraudTransactions} fraud ({kpis?.fraudPercentage}%).</li>
            <li>• Two delivery paths: a pre-scored <code>dashboard.json</code> fills these tabs, and the live <code>POST /api/score</code> endpoint scores new transactions on demand.</li>
            <li>• Customer in view: <b>{customer}</b> with {seqLen} transactions.</li>
          </ul>
        </>
      ),
    },
    {
      key: "features", icon: Wrench, title: "2 · Feature engineering",
      color: "#8b5cf6",
      body: (
        <>
          <p className="text-sm">
            Raw columns alone are weak, so we engineer <b>{nFeat} numeric features</b> per
            transaction (<code>feature_engineering.py</code>) and scale them
            (<code>StandardScaler</code> fit on the training data only — no leakage).
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {["amount","oldbalanceOrg","newbalanceOrig","amount_to_balance_ratio","zero_balance_flag","high_amount_flag","errorBalanceOrig","errorBalanceDest","type_encoded","transaction_count"].map((f) => (
              <span key={f} className="pill bg-navy-700 text-muted text-[11px]">{f}</span>
            ))}
          </div>
          <p className="mt-2 text-xs text-muted">
            The strongest are the <b>balance-error</b> signals — fraud breaks the double-entry
            bookkeeping, so these catch it.
          </p>
        </>
      ),
    },
    {
      key: "sequence", icon: Layers, title: "3 · Flat table → sequences",
      color: "#16a34a",
      body: (
        <>
          <p className="text-sm">
            This is the key conversion (<code>sequence_builder.py</code>). The flat table is grouped
            <b> per customer</b> and sorted by time, then a sliding window of the last <b>{L}</b>{" "}
            transactions becomes one training example. Short histories are <b>zero-padded and
            masked</b> so they still work.
          </p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <div className="rounded-lg border border-navy-600/60 bg-navy-900/50 p-2.5 text-xs">
              <div className="mb-1 font-bold text-muted">BEFORE — flat rows</div>
              <code className="text-ink">step, type, amount, … isFraud</code><br/>
              <code className="text-muted">one row = one transaction</code>
            </div>
            <div className="rounded-lg border border-accent/40 bg-accent/10 p-2.5 text-xs">
              <div className="mb-1 font-bold text-accent-cyan">AFTER — 3D sequences</div>
              <code className="text-ink">X = ( samples, {L}, {nFeat} )</code><br/>
              <code className="text-ink">y = isFraud of current txn</code>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted">
            For <b>{customer}</b>: {seqLen} transactions → a window of {Math.min(seqLen, L)} time
            steps × {nFeat} features feeds the model.
          </p>
        </>
      ),
    },
    {
      key: "lstm", icon: BrainCircuit, title: "4 · Why LSTM / RNN",
      color: "#f59e0b",
      body: (
        <>
          <p className="text-sm">
            A plain model judges one transaction alone. An <b>RNN</b> reads the window <b>in order</b>,
            and an <b>LSTM</b> keeps a <b>memory</b> (64 hidden units) of what mattered earlier and
            forgets noise — so it judges each transaction <b>in the context of the history</b>.
          </p>
          <ul className="mt-2 space-y-1 text-sm text-muted">
            <li>• <b>Order is signal:</b> a spike after a calm history reads as risk; the same spike in a noisy account may not.</li>
            <li>• <b>Memory beats snapshots:</b> the LSTM remembers the build-up; a point model can't.</li>
            <li>• <b>Proven here:</b> sequence models (LSTM/GRU) beat the order-blind Dense baseline on PR-AUC — that gap is the value of memory.</li>
          </ul>
        </>
      ),
    },
    {
      key: "score", icon: Gauge, title: "5 · Score → action",
      color: finalP >= HIGH_THRESHOLD ? "#dc2626" : "#16a34a",
      body: (
        <>
          <p className="text-sm">
            The final memory state is turned into one <b>fraud probability</b>, calibrated so the
            number is honest, then mapped to a business action by transparent rules
            (<code>business_rules.py</code>).
          </p>
          <div className="mt-2 flex items-center gap-2 text-sm">
            <RiskBadge probability={finalP} />
            <span>→ <b>{riskBand(finalP).action}</b></span>
          </div>
          <p className="mt-2 text-xs text-muted">
            Bands: &lt;0.30 Approve · 0.30–0.70 Review / OTP · &gt;0.70 Block. Thresholds are a
            business lever, not a fixed technical number.
          </p>
        </>
      ),
    },
    {
      key: "dash", icon: MonitorSmartphone, title: "6 · Into the dashboard",
      color: "#2563eb",
      body: (
        <>
          <p className="text-sm">
            Scores flow back to the screen two ways: <code>export_dashboard_data.py</code> writes a
            pre-computed <code>dashboard.json</code> (these charts, tables, this customer view), and
            the React app calls <code>POST /api/score</code> for live, on-demand scoring on the
            Fraud Risk Scoring tab.
          </p>
          <p className="mt-2 text-xs text-muted">
            Everything you see — KPIs, the timeline above, the LSTM flow, the alert queue — is this
            same trained model's output rendered for a human to act on.
          </p>
        </>
      ),
    },
  ];

  const active = STEPS[step];
  return (
    <div>
      {/* clickable step tabs */}
      <div className="mb-4 flex flex-wrap gap-2">
        {STEPS.map((s, i) => {
          const on = i === step;
          return (
            <button key={s.key} onClick={() => setStep(i)}
              className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
                on ? "border-accent bg-accent/15 text-accent-cyan"
                   : "border-navy-600 bg-navy-800/60 text-muted hover:border-accent/60"}`}>
              <s.icon size={13} /> {s.title}
            </button>
          );
        })}
      </div>

      {/* active step content */}
      <div className="rounded-xl border-l-4 border border-navy-600/60 bg-navy-900/40 p-4"
           style={{ borderLeftColor: active.color }}>
        <div className="mb-2 flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-lg"
                style={{ background: `${active.color}22`, color: active.color }}>
            <active.icon size={16} />
          </span>
          <h3 className="text-sm font-bold text-ink">{active.title}</h3>
        </div>
        {active.body}
      </div>

      {/* prev / next */}
      <div className="mt-3 flex items-center justify-between text-xs">
        <button className="btn-ghost !py-1" disabled={step === 0}
                onClick={() => setStep((s) => Math.max(0, s - 1))}>← Previous</button>
        <span className="text-muted">Step {step + 1} of {STEPS.length}</span>
        <button className="btn-ghost !py-1" disabled={step === STEPS.length - 1}
                onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))}>Next →</button>
      </div>
    </div>
  );
}

// Visual: the input window → LSTM memory cell → fraud score.
// Each transaction is a "token" the LSTM reads in order; arrows show memory
// being carried forward (the hidden state h_t).
function LstmFlow({ steps, finalP }) {
  const band = riskBand(finalP);
  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-w-max items-stretch gap-2">
        {/* input tokens */}
        {steps.map((t, i) => {
          const rel = i - (steps.length - 1); // 0 = current (t), -1 = t-1, ...
          const lbl = rel === 0 ? "t" : `t${rel}`;
          const p = t.fraud_probability ?? 0;
          const dot = riskBand(p).color;
          const drained = t.oldbalanceOrg > 0 && t.newbalanceOrig <= 1;
          return (
            <div key={i} className="flex items-center">
              <div className="w-28 rounded-xl border border-navy-600/60 bg-navy-900/50 p-2.5 text-center">
                <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-accent-cyan">{lbl}</div>
                <div className="text-[11px] text-muted">{t.type}</div>
                <div className="text-sm font-bold text-ink">{Number(t.amount).toLocaleString()}</div>
                <div className="mt-1 flex items-center justify-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full" style={{ background: dot }} />
                  <span className="text-[10px] text-muted">{Math.round(p * 100)}%</span>
                </div>
                {drained && <div className="mt-1 text-[9px] font-semibold text-tone-danger">drained→0</div>}
              </div>
              <ArrowRight size={16} className="mx-1 shrink-0 text-accent-cyan" />
            </div>
          );
        })}

        {/* LSTM memory cell */}
        <div className="flex items-center">
          <div className="grid w-32 place-items-center rounded-xl border-2 border-accent/50 bg-accent/10 p-2.5 text-center">
            <Cpu size={20} className="text-accent-cyan" />
            <div className="mt-1 text-xs font-bold text-ink">LSTM memory</div>
            <div className="text-[10px] text-muted">hidden state h<sub>t</sub></div>
            <div className="text-[9px] text-muted">64 units</div>
          </div>
          <ArrowRight size={16} className="mx-1 shrink-0 text-accent-cyan" />
        </div>

        {/* fraud score output */}
        <div className="grid w-32 place-items-center rounded-xl border-2 p-2.5 text-center"
             style={{ borderColor: band.color, background: `${band.color}1a` }}>
          <div className="text-[10px] font-bold uppercase tracking-wider text-muted">Fraud score</div>
          <div className="text-2xl font-extrabold text-ink">{Math.round(finalP * 100)}%</div>
          <span className="pill mt-1 text-white" style={{ background: band.color }}>{band.label}</span>
          <div className="mt-1 text-[10px] text-muted">{band.action}</div>
        </div>
      </div>
    </div>
  );
}
