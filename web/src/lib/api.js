// Thin client for the FraudShield FastAPI backend.
// In dev, Vite proxies /api -> http://localhost:8000. In production the same
// FastAPI server serves the built app, so /api is same-origin.

const BASE = "/api";

async function jget(path) {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`GET ${path} -> ${r.status}`);
  return r.json();
}

async function jpost(path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    throw new Error(detail.detail || `POST ${path} -> ${r.status}`);
  }
  return r.json();
}

export const api = {
  // Is the backend reachable at all? (decides API vs static-file mode)
  async available() {
    try {
      const r = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(2500) });
      return r.ok;
    } catch {
      return false;
    }
  },
  status: () => jget("/status"),
  dashboard: (refresh = false) => jget(`/dashboard${refresh ? "?refresh=true" : ""}`),
  score: (transaction, history = null) => jpost("/score", { transaction, history }),
  scoreBatch: (transactions) => jpost("/score/batch", { transactions }),
  train: (epochs) => jpost(`/train${epochs ? `?epochs=${epochs}` : ""}`, {}),
  async uploadDataset(file) {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(`${BASE}/dataset`, { method: "POST", body: fd });
    if (!r.ok) {
      const detail = await r.json().catch(() => ({}));
      throw new Error(detail.detail || `Upload failed (${r.status})`);
    }
    return r.json();
  },
};
