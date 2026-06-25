import {
  CheckCircle2, AlertTriangle, Scale, Rocket, Zap, ShieldCheck, RefreshCw, Brain, Cloud,
} from "lucide-react";
import { PageHeader, Card, Banner } from "../components/ui.jsx";

const BLOCKS = [
  {
    title: "Business Recommendations",
    icon: CheckCircle2,
    accent: "#16a34a",
    items: [
      "Deploy fraud scoring before payment approval — block losses before money leaves.",
      "Use the three-band action policy: auto-approve low, OTP/review medium, block high.",
      "Prioritise the fraud team on the high-risk queue instead of reviewing everything.",
      "Tune the threshold to the bank's risk appetite (recall vs false alarms).",
      "Monitor model drift monthly and retrain regularly.",
    ],
  },
  {
    title: "Limitations",
    icon: AlertTriangle,
    accent: "#f59e0b",
    items: [
      "The demo runs on synthetic PaySim-style data; real bank data is private.",
      "Fraud patterns evolve — a model trained today will decay over time.",
      "False positives inconvenience genuine customers and must be minimised.",
      "The sample dataset is small and balanced for demonstration, not real imbalance.",
    ],
  },
  {
    title: "Ethics & Responsible Use",
    icon: Scale,
    accent: "#38bdf8",
    items: [
      "Human-in-the-loop: the model recommends, a human decides on high-impact cases.",
      "Data privacy: transaction data is sensitive and must be protected.",
      "Fairness: monitor that the model does not unfairly target customer groups.",
      "Transparency: every alert ships with a plain-language reason.",
    ],
  },
];

const FUTURE = [
  { icon: Zap, label: "Real-time fraud API", text: "Score each payment in milliseconds." },
  { icon: ShieldCheck, label: "OTP / SMS step-up", text: "Verify medium-risk transactions." },
  { icon: RefreshCw, label: "Analyst feedback loop", text: "Confirmed outcomes retrain the model." },
  { icon: Brain, label: "Explainable AI (SHAP)", text: "Richer per-feature attributions." },
  { icon: Cloud, label: "Cloud deployment", text: "Scalable, with auto-retraining." },
];

export default function Recommendations() {
  return (
    <>
      <PageHeader icon={CheckCircle2} title="Recommendations"
        subtitle="Business guidance, limitations, ethics and the road ahead" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {BLOCKS.map((b) => (
          <Card key={b.title}>
            <div className="mb-3 flex items-center gap-2">
              <span className="grid h-9 w-9 place-items-center rounded-lg"
                    style={{ background: `${b.accent}22`, color: b.accent }}>
                <b.icon size={18} />
              </span>
              <h2 className="text-base font-semibold text-white">{b.title}</h2>
            </div>
            <ul className="space-y-2 text-sm text-ink/90">
              {b.items.map((it, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full"
                        style={{ background: b.accent }} />
                  <span>{it}</span>
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </div>

      <div className="mt-4">
        <Card>
          <div className="mb-3 flex items-center gap-2">
            <Rocket size={18} className="text-accent-cyan" />
            <h2 className="text-base font-semibold text-white">Future Scope</h2>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-5">
            {FUTURE.map((f) => (
              <div key={f.label} className="rounded-xl border border-navy-600/60 bg-navy-900/50 p-4">
                <f.icon size={20} className="mb-2 text-accent-cyan" />
                <div className="text-sm font-semibold text-white">{f.label}</div>
                <div className="mt-1 text-xs text-muted">{f.text}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Banner tone="info" title="FraudShield AI is a decision-support tool.">
        The goal is to make the fraud team faster and the customer safer — never to replace human
        judgement on high-impact decisions.
      </Banner>
    </>
  );
}
