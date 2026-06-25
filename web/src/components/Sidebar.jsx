import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Database, Target, GitBranch, Search, LineChart,
  Lightbulb, Bell, PiggyBank, CheckCircle2, ShieldCheck,
} from "lucide-react";

export const NAV = [
  { to: "/", label: "Executive Overview", icon: LayoutDashboard, end: true },
  { to: "/dataset", label: "Dataset Explorer", icon: Database },
  { to: "/scoring", label: "Fraud Risk Scoring", icon: Target },
  { to: "/sequence", label: "Sequence Analyzer", icon: GitBranch },
  { to: "/insights", label: "Fraud Pattern Insights", icon: Search },
  { to: "/performance", label: "Model Performance", icon: LineChart },
  { to: "/explainability", label: "Explainability", icon: Lightbulb },
  { to: "/alerts", label: "Alert Center", icon: Bell },
  { to: "/impact", label: "Business Impact", icon: PiggyBank },
  { to: "/recommendations", label: "Recommendations", icon: CheckCircle2 },
];

export default function Sidebar({ open, onClose }) {
  return (
    <>
      {/* mobile overlay */}
      <div
        className={`fixed inset-0 z-30 bg-black/50 transition-opacity lg:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
      />
      <aside
        className={`fixed z-40 flex h-full w-72 flex-col border-r border-navy-700/70 bg-navy-900/95 backdrop-blur transition-transform lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-3 px-5 py-5">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-accent-bright to-accent-cyan text-white shadow-glow">
            <ShieldCheck size={24} />
          </span>
          <div>
            <div className="text-lg font-black tracking-tight text-white">FraudShield AI</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-accent-cyan">
              Fraud Sequence Detection
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onClose}
              className={({ isActive }) =>
                `nav-link ${isActive ? "nav-link-active" : ""}`
              }
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-navy-700/70 px-5 py-4 text-[11px] leading-relaxed text-muted">
          <div className="font-semibold text-ink/80">MAIB Sept 25 · Term 3</div>
          Deep Learning Project · LSTM / RNN
        </div>
      </aside>
    </>
  );
}
