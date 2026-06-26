// Reusable presentational atoms used across all pages.
import { riskBand } from "../lib/risk.js";
import { probToPct } from "../lib/format.js";

export function PageHeader({ title, subtitle, icon: Icon }) {
  return (
    <div className="mb-6 overflow-hidden rounded-2xl border border-navy-600/60 bg-gradient-to-r from-navy-800 via-navy-700 to-navy-800 p-6 shadow-card">
      <div className="flex items-center gap-3">
        {Icon ? (
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-accent/15 text-accent-cyan">
            <Icon size={22} />
          </span>
        ) : null}
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-ink">{title}</h1>
          {subtitle ? <p className="mt-0.5 text-sm text-muted">{subtitle}</p> : null}
        </div>
      </div>
    </div>
  );
}

export function Section({ title, right, children }) {
  return (
    <div className="mb-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="section-title">{title}</h2>
        {right}
      </div>
      {children}
    </div>
  );
}

export function Card({ className = "", children }) {
  return <div className={`card card-pad ${className}`}>{children}</div>;
}

export function KpiCard({ label, value, sub, accent = "#3b82f6", icon: Icon }) {
  return (
    <div
      className="card card-pad relative overflow-hidden"
      style={{ borderTopColor: accent, borderTopWidth: 2 }}
    >
      <div className="flex items-start justify-between">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">
          {label}
        </div>
        {Icon ? (
          <span style={{ color: accent }}>
            <Icon size={18} />
          </span>
        ) : null}
      </div>
      <div className="mt-2 text-2xl font-extrabold text-ink">{value}</div>
      {sub ? <div className="mt-1 text-xs text-muted">{sub}</div> : null}
    </div>
  );
}

export function RiskBadge({ probability, label }) {
  const band = riskBand(probability);
  return (
    <span className="pill text-white" style={{ background: band.color }}>
      {label ?? band.label} · {probToPct(probability)}
    </span>
  );
}

export function Banner({ tone = "warn", title, children }) {
  const tones = {
    warn: "border-risk-med/40 bg-risk-med/10 text-tone-warn",
    info: "border-accent/40 bg-accent/10 text-tone-info",
    danger: "border-risk-high/40 bg-risk-high/10 text-tone-danger",
  };
  return (
    <div className={`mb-5 rounded-xl border px-4 py-3 text-sm ${tones[tone]}`}>
      {title ? <span className="font-bold">{title} </span> : null}
      {children}
    </div>
  );
}

// Demo / data-source banners driven by the dashboard meta block.
export function ModeBanner({ meta }) {
  if (!meta) return null;
  return (
    <>
      {meta.mode === "demo" && (
        <Banner tone="warn" title="⚠️ Trained model not found — running in demo mode.">
          Fraud scores come from transparent business rules, not a trained LSTM. Train
          the model in the notebook to switch to real scoring.
        </Banner>
      )}
      {meta.source !== "real" && (
        <Banner tone="info" title="ℹ️ Synthetic sample data (demo only).">
          Add the real PaySim file at <code>data/paysim.csv</code> and re-run the export
          for genuine results.
        </Banner>
      )}
    </>
  );
}

export function Table({ columns, rows, renderCell }) {
  return (
    <div className="overflow-auto rounded-xl border border-navy-600/60">
      <table className="min-w-full">
        <thead className="sticky top-0 bg-navy-900/95 backdrop-blur">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className="th">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-navy-700/60">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-navy-700/40">
              {columns.map((c) => (
                <td key={c.key} className="td">
                  {renderCell ? renderCell(c, row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
