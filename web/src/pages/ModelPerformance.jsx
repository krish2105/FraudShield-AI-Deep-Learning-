import { useMemo, useState } from "react";
import { LineChart as LineIcon } from "lucide-react";
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ReferenceArea, ReferenceLine, Cell,
} from "recharts";
import { PageHeader, Section, Card, Banner } from "../components/ui.jsx";

const MODEL_COLORS = {
  lstm: "#38bdf8", gru: "#a78bfa", cnn: "#f59e0b", dense_nn: "#94a3b8",
};
const MODEL_LABEL = {
  lstm: "LSTM", gru: "GRU", cnn: "1D-CNN", dense_nn: "Dense baseline", autoencoder: "Autoencoder",
};
const AXIS = { stroke: "#3b4a6b", tick: { fill: "#8aa0c2", fontSize: 11 } };
const GRID = "#16223f";

// Linear interpolation of a curve onto a common x-grid (for overlaying curves).
function resample(points, xKey, yKey, grid) {
  if (!points?.length) return grid.map(() => null);
  const pts = [...points].sort((a, b) => a[xKey] - b[xKey]);
  return grid.map((x) => {
    if (x <= pts[0][xKey]) return pts[0][yKey];
    if (x >= pts[pts.length - 1][xKey]) return pts[pts.length - 1][yKey];
    for (let i = 1; i < pts.length; i++) {
      if (x <= pts[i][xKey]) {
        const a = pts[i - 1], b = pts[i];
        const t = (x - a[xKey]) / ((b[xKey] - a[xKey]) || 1);
        return a[yKey] + t * (b[yKey] - a[yKey]);
      }
    }
    return null;
  });
}

export default function ModelPerformance({ data }) {
  const curves = data.curves || {};
  const models = curves.models || {};
  const metrics = data.metrics || {};
  const supervised = Object.keys(models);
  const primary = curves.primary || data.meta?.primary || "lstm";
  const notTrained = !supervised.length || metrics.status === "NOT_TRAINED";

  const [sel, setSel] = useState(primary);
  const m = metrics[sel] || {};

  // --- overlaid PR & ROC across models -------------------------------------
  const grid = useMemo(() => Array.from({ length: 51 }, (_, i) => i / 50), []);
  const prData = useMemo(() => {
    const cols = supervised.map((name) => ({ name, y: resample(models[name].pr, "recall", "precision", grid) }));
    return grid.map((x, i) => ({ x, ...Object.fromEntries(cols.map((c) => [c.name, c.y[i]])) }));
  }, [models, supervised, grid]);
  const rocData = useMemo(() => {
    const cols = supervised.map((name) => ({ name, y: resample(models[name].roc, "fpr", "tpr", grid) }));
    return grid.map((x, i) => ({ x, ...Object.fromEntries(cols.map((c) => [c.name, c.y[i]])) }));
  }, [models, supervised, grid]);

  // --- comparison bars -----------------------------------------------------
  const comparison = useMemo(
    () => supervised.concat(metrics.autoencoder ? ["autoencoder"] : []).map((name) => ({
      model: MODEL_LABEL[name] || name,
      "PR-AUC": metrics[name]?.pr_auc ?? 0,
      Recall: metrics[name]?.recall ?? 0,
      "F1": metrics[name]?.f1 ?? 0,
    })),
    [metrics, supervised]
  );

  // --- selected-model training history -------------------------------------
  const history = useMemo(() => {
    const h = models[sel]?.history;
    if (!h) return [];
    return h.train_loss.map((tl, i) => ({
      epoch: i + 1, train_loss: tl, val_loss: h.val_loss[i], val_pr_auc: h.val_pr_auc?.[i],
    }));
  }, [models, sel]);

  const sweep = models[sel]?.threshold || [];
  const dist = models[sel]?.score_dist || [];
  const ae = curves.autoencoder;
  const cm = metrics[primary]?.confusion_matrix || curves.confusion_matrix;

  return (
    <>
      <PageHeader icon={LineIcon} title="Model Performance"
        subtitle="Deep-learning evaluation: LSTM · GRU · 1D-CNN · Dense baseline · Autoencoder" />

      {notTrained ? (
        <Banner tone="warn" title="⚠️ No trained-model metrics yet.">
          Train the models (notebook, or the Dataset & Model Manager) to populate these graphs.
        </Banner>
      ) : (
        <Banner tone="info" title={`Primary model: ${MODEL_LABEL[primary] || primary}.`}>
          {metrics.note} We select the primary model by best <b>PR-AUC</b> (the right metric for rare
          fraud). Recall is the operational priority — missing fraud is the costly error.
        </Banner>
      )}

      {/* model comparison */}
      <Card>
        <Section title="Model Comparison (higher is better)">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={comparison} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
              <XAxis dataKey="model" {...AXIS} />
              <YAxis domain={[0, 1]} {...AXIS} />
              <Tooltip cursor={{ fill: "rgba(56,189,248,0.06)" }} />
              <Legend wrapperStyle={{ color: "#8aa0c2", fontSize: 12 }} />
              <Bar dataKey="PR-AUC" fill="#38bdf8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Recall" fill="#16a34a" radius={[4, 4, 0, 0]} />
              <Bar dataKey="F1" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Section>
      </Card>

      {/* PR + ROC overlays */}
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <Section title="Precision–Recall Curves (the headline for imbalance)">
            <CurveChart data={prData} models={supervised} metrics={metrics} aucKey="pr_auc"
                        xLabel="Recall" />
          </Section>
        </Card>
        <Card>
          <Section title="ROC Curves">
            <CurveChart data={rocData} models={supervised} metrics={metrics} aucKey="roc_auc"
                        xLabel="False positive rate" diagonal />
          </Section>
        </Card>
      </div>

      {/* per-model deep dive */}
      <div className="mt-4">
        <Card>
          <Section title="Per-Model Deep Dive"
            right={
              <select className="input" value={sel} onChange={(e) => setSel(e.target.value)}>
                {supervised.map((n) => <option key={n} value={n}>{MODEL_LABEL[n] || n}</option>)}
              </select>
            }>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
              {["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"].map((k) => (
                <div key={k} className="rounded-xl border border-navy-600/60 bg-navy-900/50 p-3 text-center">
                  <div className="text-[11px] uppercase tracking-wider text-muted">{k.replace("_", "-")}</div>
                  <div className="mt-1 text-xl font-bold text-ink">
                    {typeof m[k] === "number" ? m[k].toFixed(3) : "—"}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div>
                <h3 className="mb-1 text-sm font-semibold text-ink/90">Training History</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={history} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
                    <XAxis dataKey="epoch" {...AXIS} />
                    <YAxis {...AXIS} />
                    <Tooltip />
                    <Legend wrapperStyle={{ color: "#8aa0c2", fontSize: 11 }} />
                    <Line type="monotone" dataKey="train_loss" stroke="#f59e0b" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="val_loss" stroke="#dc2626" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="val_pr_auc" stroke="#38bdf8" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div>
                <h3 className="mb-1 text-sm font-semibold text-ink/90">
                  Threshold Sweep (risk bands shaded)
                </h3>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={sweep} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
                    <ReferenceArea x1={0} x2={0.30} fill="#16a34a" fillOpacity={0.07} />
                    <ReferenceArea x1={0.30} x2={0.70} fill="#f59e0b" fillOpacity={0.07} />
                    <ReferenceArea x1={0.70} x2={1} fill="#dc2626" fillOpacity={0.07} />
                    <XAxis dataKey="threshold" type="number" domain={[0, 1]} {...AXIS} />
                    <YAxis domain={[0, 1]} {...AXIS} />
                    <Tooltip />
                    <Legend wrapperStyle={{ color: "#8aa0c2", fontSize: 11 }} />
                    <Line type="monotone" dataKey="precision" stroke="#38bdf8" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="recall" stroke="#16a34a" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="f1" stroke="#f59e0b" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="mt-4">
              <h3 className="mb-1 text-sm font-semibold text-ink/90">
                Score Separation (genuine vs fraud)
              </h3>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={dist} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
                  <XAxis dataKey="score" {...AXIS} />
                  <YAxis {...AXIS} />
                  <Tooltip />
                  <Legend wrapperStyle={{ color: "#8aa0c2", fontSize: 11 }} />
                  <Bar dataKey="genuine" fill="#2563eb" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="fraud" fill="#dc2626" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Section>
        </Card>
      </div>

      {/* confusion matrix + autoencoder */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <Section title={`Confusion Matrix — ${MODEL_LABEL[primary] || primary}`}>
            {cm ? <ConfusionMatrix cm={cm} /> : <p className="text-sm text-muted">Train to populate.</p>}
          </Section>
        </Card>
        <Card>
          <Section title="Autoencoder — Reconstruction Error (novel-fraud detector)">
            {ae?.recon_dist ? (
              <>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={ae.recon_dist} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
                    <XAxis dataKey="error" {...AXIS} />
                    <YAxis {...AXIS} />
                    <Tooltip />
                    <Legend wrapperStyle={{ color: "#8aa0c2", fontSize: 11 }} />
                    <ReferenceLine x={ae.threshold} stroke="#f59e0b" strokeDasharray="4 4"
                                   label={{ value: "threshold", fill: "#f59e0b", fontSize: 10 }} />
                    <Bar dataKey="genuine" fill="#2563eb" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="fraud" fill="#dc2626" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <p className="mt-2 text-xs text-muted">
                  Trained on genuine traffic only; fraud sits in the high-error tail beyond the
                  threshold. Catches anomalies even without fraud labels.
                </p>
              </>
            ) : <p className="text-sm text-muted">Train to populate.</p>}
          </Section>
        </Card>
      </div>

      <Card className="mt-4">
        <Section title="What the Metrics Mean">
          <div className="overflow-auto rounded-xl border border-navy-600/60">
            <table className="min-w-full">
              <thead className="bg-navy-900/95"><tr>
                <th className="th">Metric</th><th className="th">Meaning</th><th className="th">Why it matters</th>
              </tr></thead>
              <tbody className="divide-y divide-navy-700/60">
                {[
                  ["Recall", "Of real frauds, how many caught", "MOST important — missing fraud is costly"],
                  ["Precision", "Of flagged, how many were real", "Fewer false alarms for customers"],
                  ["PR-AUC", "Precision/recall on the rare class", "Best summary for imbalanced fraud"],
                  ["ROC-AUC", "Ranking quality across thresholds", "1.0 perfect, 0.5 random"],
                  ["F1", "Balance of precision & recall", "Single combined score"],
                ].map(([a, b, c]) => (
                  <tr key={a}><td className="td font-semibold">{a}</td>
                    <td className="td whitespace-normal text-muted">{b}</td>
                    <td className="td whitespace-normal text-muted">{c}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      </Card>
    </>
  );
}

function CurveChart({ data, models, metrics, aucKey, xLabel, diagonal }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 6 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
        <XAxis dataKey="x" type="number" domain={[0, 1]} {...AXIS}
               label={{ value: xLabel, position: "insideBottom", offset: -4, fill: "#8aa0c2", fontSize: 11 }} />
        <YAxis domain={[0, 1]} {...AXIS} />
        <Tooltip />
        <Legend wrapperStyle={{ color: "#8aa0c2", fontSize: 11 }} />
        {diagonal && (
          <Line data={[{ x: 0, d: 0 }, { x: 1, d: 1 }]} dataKey="d" stroke="#475569"
                strokeDasharray="4 4" dot={false} legendType="none" name="random" />
        )}
        {models.map((name) => (
          <Line key={name} type="monotone" dataKey={name} stroke={MODEL_COLORS[name] || "#3b82f6"}
                strokeWidth={2} dot={false} connectNulls
                name={`${MODEL_LABEL[name] || name} (${(metrics[name]?.[aucKey] ?? 0).toFixed(3)})`} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

function ConfusionMatrix({ cm }) {
  const labels = ["Genuine", "Fraud"];
  const max = Math.max(...cm.flat().map(Number), 1);
  return (
    <table className="w-full text-center text-sm">
      <thead><tr>
        <th className="p-2"></th>{labels.map((l) => <th key={l} className="p-2 text-muted">Pred {l}</th>)}
      </tr></thead>
      <tbody>
        {cm.map((row, i) => (
          <tr key={i}>
            <td className="p-2 text-muted">Actual {labels[i]}</td>
            {row.map((v, j) => {
              const correct = i === j;
              const intensity = Math.min(0.8, Number(v) / max);
              return (
                <td key={j} className="p-2">
                  <div className="grid h-16 place-items-center rounded-lg font-bold text-white"
                       style={{ background: correct
                         ? `rgba(22,163,74,${0.2 + intensity * 0.6})`
                         : `rgba(220,38,38,${0.2 + intensity * 0.6})` }}>
                    {v}
                  </div>
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
