import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import { Menu, Loader2, ShieldAlert, SlidersHorizontal, Sun, Moon } from "lucide-react";
import Sidebar from "./components/Sidebar.jsx";
import DatasetManager from "./components/DatasetManager.jsx";
import { useDashboard } from "./lib/data.js";
import { useTheme } from "./lib/theme.js";

import ExecutiveOverview from "./pages/ExecutiveOverview.jsx";
import DatasetExplorer from "./pages/DatasetExplorer.jsx";
import FraudScoring from "./pages/FraudScoring.jsx";
import SequenceAnalyzer from "./pages/SequenceAnalyzer.jsx";
import FraudInsights from "./pages/FraudInsights.jsx";
import ModelPerformance from "./pages/ModelPerformance.jsx";
import Explainability from "./pages/Explainability.jsx";
import AlertCenter from "./pages/AlertCenter.jsx";
import BusinessImpact from "./pages/BusinessImpact.jsx";

export default function App() {
  const [sidebar, setSidebar] = useState(false);
  const [manager, setManager] = useState(false);
  const { data, loading, error, reload } = useDashboard();
  const { theme, toggle } = useTheme();

  return (
    <div className="app-bg flex min-h-screen text-ink">
      <Sidebar open={sidebar} onClose={() => setSidebar(false)} />
      <DatasetManager open={manager} onClose={() => setManager(false)} onChanged={() => reload(true)} />

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-navy-700/70 bg-navy-950/80 px-4 py-3 backdrop-blur lg:px-8">
          <button
            className="btn-ghost lg:hidden"
            onClick={() => setSidebar(true)}
            aria-label="Open menu"
          >
            <Menu size={18} />
          </button>
          <div className="hidden text-sm text-muted lg:block">
            Payment Fraud Sequence Detection · <span className="text-ink">LSTM / RNN</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="icon-btn"
              onClick={toggle}
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
              title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            >
              {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
            </button>
            <button
              className="flex items-center gap-2 rounded-lg border border-navy-600 bg-navy-800/60 px-2.5 py-1.5 transition hover:border-accent hover:bg-navy-700"
              onClick={() => setManager(true)}
              title="Open Dataset & Model Manager"
            >
              {data?.meta && (
                <span
                  className={`pill ${
                    data.meta.mode === "demo"
                      ? "bg-risk-med/20 text-risk-med"
                      : "bg-risk-low/20 text-risk-low"
                  }`}
                >
                  {data.meta.mode === "demo" ? "Demo mode" : "Model mode"}
                </span>
              )}
              <span className="pill bg-navy-700 text-muted">
                {data?.meta?.source === "real" ? "Real data" : "Sample data"}
              </span>
              <SlidersHorizontal size={15} className="text-muted" />
            </button>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 lg:px-8">
          {loading && (
            <div className="grid h-[60vh] place-items-center text-muted">
              <div className="flex items-center gap-3">
                <Loader2 className="animate-spin" /> Loading FraudShield data…
              </div>
            </div>
          )}

          {error && (
            <div className="grid h-[60vh] place-items-center">
              <div className="card card-pad max-w-lg text-center">
                <ShieldAlert className="mx-auto mb-3 text-risk-high" size={36} />
                <h2 className="mb-2 text-lg font-bold text-ink">
                  Could not load dashboard data
                </h2>
                <p className="text-sm text-muted">{String(error.message || error)}</p>
                <p className="mt-3 text-xs text-muted">
                  Run <code className="text-accent-cyan">python src/export_dashboard_data.py</code>{" "}
                  from the project root, then refresh.
                </p>
              </div>
            </div>
          )}

          {data && (
            <Routes>
              <Route path="/" element={<ExecutiveOverview data={data} />} />
              <Route path="/dataset" element={<DatasetExplorer data={data} />} />
              <Route path="/scoring" element={<FraudScoring data={data} />} />
              <Route path="/sequence" element={<SequenceAnalyzer data={data} />} />
              <Route path="/insights" element={<FraudInsights data={data} />} />
              <Route path="/performance" element={<ModelPerformance data={data} />} />
              <Route path="/explainability" element={<Explainability data={data} />} />
              <Route path="/alerts" element={<AlertCenter data={data} />} />
              <Route path="/impact" element={<BusinessImpact data={data} />} />
            </Routes>
          )}
        </main>
      </div>
    </div>
  );
}
