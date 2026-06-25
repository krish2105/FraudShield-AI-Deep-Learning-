import { useState } from "react";
import Papa from "papaparse";
import { Target, Upload, Download, Play, Zap, Loader2 } from "lucide-react";
import { PageHeader, Section, Card, KpiCard, RiskBadge, Banner } from "../components/ui.jsx";
import { BarChartCard } from "../components/charts.jsx";
import { demoScoreRow, riskBand, LOW_THRESHOLD, HIGH_THRESHOLD } from "../lib/risk.js";
import { formatNumber, probToPct } from "../lib/format.js";
import { api } from "../lib/api.js";

// --- Live single-transaction scoring (calls the trained model via the API) ---
const PRESETS = {
  "Full account sweep (fraud-like)": { type: "TRANSFER", amount: 52000, oldbalanceOrg: 52000, newbalanceOrig: 0, oldbalanceDest: 0, newbalanceDest: 0 },
  "Normal small payment": { type: "PAYMENT", amount: 120, oldbalanceOrg: 8000, newbalanceOrig: 7880, oldbalanceDest: 0, newbalanceDest: 0 },
  "Large but consistent transfer": { type: "TRANSFER", amount: 9000, oldbalanceOrg: 40000, newbalanceOrig: 31000, oldbalanceDest: 5000, newbalanceDest: 14000 },
};

function LiveScore() {
  const [txn, setTxn] = useState({
    step: 12, type: "TRANSFER", amount: 52000, nameOrig: "C-DEMO",
    oldbalanceOrg: 52000, newbalanceOrig: 0, nameDest: "C-MULE",
    oldbalanceDest: 0, newbalanceDest: 0, isFraud: 0,
  });
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  function set(k, v) { setTxn((t) => ({ ...t, [k]: v })); }
  function applyPreset(name) { setTxn((t) => ({ ...t, ...PRESETS[name] })); setResult(null); }

  async function run() {
    setBusy(true); setErr(""); setResult(null);
    try {
      const r = await api.score(txn);
      setResult(r);
    } catch (e) {
      // Backend down → fall back to transparent client-side demo scoring.
      const p = demoScoreRow(txn);
      const band = riskBand(p);
      setResult({ probability: p, risk_label: band.label, recommended_action: band.action,
        color: band.color, mode: "demo" });
      setErr("Backend offline — used client-side demo scoring.");
    } finally {
      setBusy(false);
    }
  }

  const num = (k, label) => (
    <label className="text-xs">
      <span className="mb-1 block text-muted">{label}</span>
      <input type="number" className="input w-full" value={txn[k]}
             onChange={(e) => set(k, Number(e.target.value))} />
    </label>
  );

  return (
    <Card>
      <Section title="Live Transaction Scoring"
        right={<span className="pill bg-accent/15 text-accent-cyan"><Zap size={12} /> real model</span>}>
        <div className="mb-3 flex flex-wrap gap-2">
          {Object.keys(PRESETS).map((p) => (
            <button key={p} className="btn-ghost !py-1 !text-xs" onClick={() => applyPreset(p)}>{p}</button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <label className="text-xs">
            <span className="mb-1 block text-muted">Type</span>
            <select className="input w-full" value={txn.type} onChange={(e) => set("type", e.target.value)}>
              {["TRANSFER", "CASH_OUT", "PAYMENT", "CASH_IN", "DEBIT"].map((t) => <option key={t}>{t}</option>)}
            </select>
          </label>
          {num("amount", "Amount")}
          {num("oldbalanceOrg", "Sender bal before")}
          {num("newbalanceOrig", "Sender bal after")}
          {num("oldbalanceDest", "Receiver bal before")}
          {num("newbalanceDest", "Receiver bal after")}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-4">
          <button className="btn" onClick={run} disabled={busy}>
            {busy ? <Loader2 className="animate-spin" size={16} /> : <Zap size={16} />} Score transaction
          </button>
          {result && (
            <div className="flex items-center gap-3">
              <RiskBadge probability={result.probability} label={result.risk_label} />
              <span className="text-sm text-ink">→ <b>{result.recommended_action}</b></span>
              <span className="pill bg-navy-700 text-muted">{result.mode === "model" ? "trained model" : "demo rule"}</span>
            </div>
          )}
        </div>
        {err && <p className="mt-2 text-xs text-amber-300">{err}</p>}
      </Section>
    </Card>
  );
}

export default function FraudScoring({ data }) {
  const [scored, setScored] = useState(null);
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState("");

  function scoreRows(rows) {
    return rows
      .filter((r) => r && (r.amount !== undefined || r.type !== undefined))
      .map((r) => {
        const p = demoScoreRow(r);
        const band = riskBand(p);
        return { ...r, fraud_probability: p, risk_label: band.label, recommended_action: band.action };
      });
  }

  function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setFileName(file.name);
    Papa.parse(file, {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (res) => {
        try {
          const s = scoreRows(res.data);
          if (!s.length) throw new Error("No valid rows found. Expected PaySim columns.");
          setScored(s);
        } catch (err) {
          setError(err.message);
          setScored(null);
        }
      },
      error: (err) => setError(err.message),
    });
  }

  function scoreSample() {
    setError("");
    setFileName("built-in sample");
    // Re-score the sample rows with the JS demo rule for consistency.
    setScored(scoreRows(data.scoredSample.slice(0, 600)));
  }

  function downloadCsv() {
    const csv = Papa.unparse(scored);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "fraud_scored_results.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const counts = scored
    ? {
        low: scored.filter((r) => r.fraud_probability <= LOW_THRESHOLD).length,
        med: scored.filter((r) => r.fraud_probability > LOW_THRESHOLD && r.fraud_probability <= HIGH_THRESHOLD).length,
        high: scored.filter((r) => r.fraud_probability > HIGH_THRESHOLD).length,
      }
    : null;

  // histogram of scores
  const hist = scored
    ? Array.from({ length: 10 }, (_, i) => {
        const lo = i / 10, hi = (i + 1) / 10;
        return {
          band: `${lo.toFixed(1)}`,
          count: scored.filter((r) => r.fraud_probability >= lo && r.fraud_probability < hi).length,
        };
      })
    : [];

  return (
    <>
      <PageHeader icon={Target} title="Fraud Risk Scoring"
        subtitle="Score one transaction live, or a whole CSV file" />

      <LiveScore />

      <div className="mt-4" />
      <Card>
        <Section title="Input">
          <div className="flex flex-wrap items-center gap-4">
            <label className="btn cursor-pointer">
              <Upload size={16} /> Upload transactions CSV
              <input type="file" accept=".csv" className="hidden" onChange={handleUpload} />
            </label>
            <button className="btn-ghost" onClick={scoreSample}>
              <Play size={16} /> Score the built-in sample
            </button>
            {fileName && <span className="text-sm text-muted">Loaded: {fileName}</span>}
          </div>
          <p className="mt-3 text-xs text-muted">
            Expected columns: step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig, … Scoring
            here uses the transparent demo rules (mirrors the Python backend in demo mode).
          </p>
          {error && <Banner tone="danger" title="Error:">{error}</Banner>}
        </Section>
      </Card>

      {scored && (
        <>
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <KpiCard label="Low Risk → Approve" value={formatNumber(counts.low)} sub="score ≤ 0.30" accent="#16a34a" />
            <KpiCard label="Medium → Review / OTP" value={formatNumber(counts.med)} sub="0.31 – 0.70" accent="#f59e0b" />
            <KpiCard label="High → Block / Alert" value={formatNumber(counts.high)} sub="score ≥ 0.71" accent="#dc2626" />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-1">
              <Section title="Score Distribution">
                <BarChartCard data={hist} x="band" y="count" color="#3b82f6" height={260} label="Count" />
              </Section>
            </Card>
            <Card className="lg:col-span-2">
              <Section title="Scored Transactions"
                right={<button className="btn" onClick={downloadCsv}><Download size={16} /> Download CSV</button>}>
                <div className="max-h-96 overflow-auto rounded-xl border border-navy-600/60">
                  <table className="min-w-full">
                    <thead className="sticky top-0 bg-navy-900/95">
                      <tr>
                        <th className="th">Type</th><th className="th">Amount</th>
                        <th className="th">Risk</th><th className="th">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-navy-700/60">
                      {[...scored]
                        .sort((a, b) => b.fraud_probability - a.fraud_probability)
                        .slice(0, 300)
                        .map((r, i) => (
                          <tr key={i} className="hover:bg-navy-700/40">
                            <td className="td">{r.type}</td>
                            <td className="td">{Number(r.amount).toLocaleString()}</td>
                            <td className="td"><RiskBadge probability={r.fraud_probability} /></td>
                            <td className="td text-muted">{r.recommended_action}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-2 text-xs text-muted">Showing top 300 by risk.</p>
              </Section>
            </Card>
          </div>
        </>
      )}
    </>
  );
}
