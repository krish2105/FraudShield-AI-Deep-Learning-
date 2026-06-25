import { useEffect, useState } from "react";
import { X, Upload, Database, Cpu, RefreshCw, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import { api } from "../lib/api.js";

// Modal that turns the status chips into a real Dataset & Model manager:
// shows live status, uploads the real PaySim CSV, and retrains the models.
export default function DatasetManager({ open, onClose, onChanged }) {
  const [status, setStatus] = useState(null);
  const [backend, setBackend] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);

  async function refreshStatus() {
    try {
      const up = await api.available();
      setBackend(up);
      if (up) setStatus(await api.status());
    } catch {
      setBackend(false);
    }
  }

  useEffect(() => {
    if (open) {
      setMsg(null); setErr(null);
      refreshStatus();
    }
  }, [open]);

  // Poll while training is running.
  useEffect(() => {
    if (!open || !status?.training) return;
    const t = setInterval(async () => {
      const s = await api.status();
      setStatus(s);
      if (!s.training) {
        setMsg(s.message);
        onChanged?.();
        clearInterval(t);
      }
    }, 2000);
    return () => clearInterval(t);
  }, [open, status?.training]);

  if (!open) return null;

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setErr(null); setMsg(null);
    try {
      const res = await api.uploadDataset(file);
      setMsg(res.message);
      await refreshStatus();
      onChanged?.();
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleTrain() {
    setBusy(true); setErr(null); setMsg(null);
    try {
      await api.train();
      const s = await api.status();
      setStatus(s);
      setMsg("Training started — this runs in the background.");
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}>
      <div className="card w-full max-w-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-navy-600/60 px-5 py-4">
          <div className="flex items-center gap-2">
            <Database className="text-accent-cyan" size={20} />
            <h2 className="text-lg font-bold text-white">Dataset & Model Manager</h2>
          </div>
          <button onClick={onClose} className="text-muted hover:text-white"><X size={20} /></button>
        </div>

        <div className="card-pad space-y-5">
          {backend === false && (
            <div className="rounded-xl border border-risk-med/40 bg-risk-med/10 p-4 text-sm text-amber-200">
              <AlertTriangle className="mb-1 inline" size={16} /> The backend API isn't running,
              so live upload / retrain are unavailable. Start it with:
              <pre className="mt-2 overflow-auto rounded bg-navy-950 p-2 text-xs text-accent-cyan">uvicorn api.main:app --port 8000</pre>
              The dashboard still works from the precomputed snapshot.
            </div>
          )}

          {status && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Mode" value={status.mode === "model" ? "Model" : "Demo"}
                    tone={status.mode === "model" ? "good" : "warn"} />
              <Stat label="Data source" value={status.source === "real" ? "Real PaySim" : "Sample"}
                    tone={status.source === "real" ? "good" : "warn"} />
              <Stat label="Primary model" value={(status.primary || "lstm").toUpperCase()} />
              <Stat label="Training" value={status.training ? "Running…" : "Idle"}
                    tone={status.training ? "warn" : "good"} />
            </div>
          )}

          {/* Upload real PaySim */}
          <div className="rounded-xl border border-navy-600/60 bg-navy-900/50 p-4">
            <div className="mb-2 flex items-center gap-2 font-semibold text-white">
              <Upload size={16} className="text-accent-cyan" /> Connect the real PaySim dataset
            </div>
            <p className="mb-3 text-xs text-muted">
              Upload <code>paysim.csv</code> (the Kaggle PaySim file) with the standard columns. It
              replaces the sample data and refreshes every page. Then retrain so the model matches it.
            </p>
            <label className={`btn cursor-pointer ${backend === false || busy ? "pointer-events-none opacity-50" : ""}`}>
              <Upload size={16} /> Choose CSV
              <input type="file" accept=".csv" className="hidden" onChange={handleUpload}
                     disabled={backend === false || busy} />
            </label>
          </div>

          {/* Retrain */}
          <div className="rounded-xl border border-navy-600/60 bg-navy-900/50 p-4">
            <div className="mb-2 flex items-center gap-2 font-semibold text-white">
              <Cpu size={16} className="text-accent-cyan" /> Retrain models
            </div>
            <p className="mb-3 text-xs text-muted">
              Trains Dense, LSTM, GRU, 1D-CNN and the Autoencoder on the current dataset, then
              refreshes all metrics, curves and scores.
            </p>
            <button className="btn" onClick={handleTrain} disabled={backend === false || busy || status?.training}>
              {status?.training ? <Loader2 className="animate-spin" size={16} /> : <Cpu size={16} />}
              {status?.training ? "Training…" : "Train on current data"}
            </button>
          </div>

          {msg && (
            <div className="flex items-start gap-2 rounded-xl border border-risk-low/40 bg-risk-low/10 p-3 text-sm text-emerald-200">
              <CheckCircle2 size={16} className="mt-0.5" /> {msg}
            </div>
          )}
          {err && (
            <div className="flex items-start gap-2 rounded-xl border border-risk-high/40 bg-risk-high/10 p-3 text-sm text-red-200">
              <AlertTriangle size={16} className="mt-0.5" /> {err}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button className="btn-ghost" onClick={() => { refreshStatus(); onChanged?.(); }}>
              <RefreshCw size={16} /> Refresh
            </button>
            <button className="btn" onClick={onClose}>Done</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }) {
  const color = tone === "good" ? "text-emerald-300" : tone === "warn" ? "text-amber-300" : "text-white";
  return (
    <div className="rounded-lg border border-navy-600/60 bg-navy-800/60 p-3">
      <div className="text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-1 text-sm font-bold ${color}`}>{value}</div>
    </div>
  );
}
