import { useEffect, useState, useCallback } from "react";
import { api } from "./api.js";

// Loads the dashboard payload with a STALE-WHILE-REVALIDATE strategy:
//   1. paint the precomputed snapshot instantly (no waiting on the 6.3M-row
//      cold build), then
//   2. always re-fetch from the live FastAPI backend (if it's up) so the view
//      converges to the CURRENT data — e.g. right after you upload a new CSV or
//      retrain. This is what makes a browser refresh show the latest dataset
//      instead of the previous one.
const STATIC_URL = `${import.meta.env.BASE_URL}data/dashboard.json`;

let _cache = null;
let _backend = null;

async function backendUp() {
  if (_backend === null) _backend = await api.available();
  return _backend;
}

async function fetchStatic() {
  const r = await fetch(STATIC_URL, { cache: "no-store" });
  if (!r.ok) throw new Error(`Could not load dashboard.json (HTTP ${r.status})`);
  return r.json();
}

// Live data from the API (falls back to the static snapshot if the API is down).
async function fetchLive(force = false) {
  if (await backendUp()) return api.dashboard(force);
  return fetchStatic();
}

export function useDashboard() {
  const [state, setState] = useState({
    data: _cache, loading: !_cache, error: null, backend: _backend,
  });

  const applyLive = useCallback(async (force) => {
    try {
      const data = await fetchLive(force);
      _cache = data;
      setState({ data, loading: false, error: null, backend: _backend });
      return true;
    } catch (error) {
      // Only surface an error if we have nothing to show at all.
      setState((s) => s.data
        ? { ...s, loading: false, backend: _backend }
        : { data: null, loading: false, error, backend: _backend });
      return false;
    }
  }, []);

  // Explicit refresh (after upload / retrain): force a fresh API build.
  const reload = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }));
    _backend = null;            // re-probe in case the API just came up
    await applyLive(true);
  }, [applyLive]);

  useEffect(() => {
    let alive = true;
    (async () => {
      // 1) instant paint from the snapshot (if we don't already have data)
      if (!_cache) {
        try {
          const snap = await fetchStatic();
          if (alive && !_cache) {
            _cache = snap;
            setState({ data: snap, loading: false, error: null, backend: _backend });
          }
        } catch {
          /* no snapshot — the live fetch below will populate or error */
        }
      }
      // 2) revalidate from the live API so we always show the CURRENT data
      if (alive) await applyLive(false);
    })();
    return () => { alive = false; };
  }, [applyLive]);

  return { ...state, reload };
}

export function isBackendUp() {
  return _backend === true;
}
