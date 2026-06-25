// Risk bands + transparent demo scoring, mirrored from src/business_rules.py
// so the client-side "Fraud Risk Scoring" page can score an uploaded CSV with
// the exact same logic used by the Python backend in demo mode.

export const LOW_THRESHOLD = 0.3;
export const HIGH_THRESHOLD = 0.7;
export const HIGH_AMOUNT_THRESHOLD = 200000;

export const RISK = {
  LOW: { key: "LOW", label: "Low Risk", action: "Approve", color: "#16a34a" },
  MEDIUM: { key: "MEDIUM", label: "Medium Risk", action: "Manual Review / OTP", color: "#f59e0b" },
  HIGH: { key: "HIGH", label: "High Risk", action: "Block / Alert Fraud Team", color: "#dc2626" },
};

export function riskBand(p) {
  const x = Number(p) || 0;
  if (x <= LOW_THRESHOLD) return RISK.LOW;
  if (x <= HIGH_THRESHOLD) return RISK.MEDIUM;
  return RISK.HIGH;
}

// Map any label string -> band (used when reading precomputed rows).
export function bandFromLabel(label) {
  if (!label) return RISK.LOW;
  if (label.toLowerCase().startsWith("high")) return RISK.HIGH;
  if (label.toLowerCase().startsWith("medium")) return RISK.MEDIUM;
  return RISK.LOW;
}

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

// Transparent rule-based score for a single transaction object.
// Mirrors business_rules.demo_score in Python.
export function demoScoreRow(row) {
  const amount = Number(row.amount) || 0;
  const oldOrg = Number(row.oldbalanceOrg) || 0;
  const newOrg = Number(row.newbalanceOrig) || 0;
  const type = String(row.type || "PAYMENT");

  let score = 0;
  // Signal 1: high amount relative to threshold.
  score += clamp(amount / (HIGH_AMOUNT_THRESHOLD * 4), 0, 0.35);
  // Signal 2: sender balance drained to ~0.
  if (oldOrg > 0 && newOrg <= 1) score += 0.3;
  // Signal 3: amount almost equals the whole old balance.
  const ratio = oldOrg > 0 ? amount / oldOrg : 0;
  score += ratio >= 0.9 ? 0.25 : clamp(ratio * 0.1, 0, 0.25);
  // Signal 4: risky transaction types.
  if (type === "TRANSFER" || type === "CASH_OUT") score += 0.15;

  return clamp(score, 0, 0.999);
}

// Plain-English reasons for a single transaction (for Explainability page).
export function explainRow(row) {
  const reasons = [];
  const amount = Number(row.amount) || 0;
  const oldOrg = Number(row.oldbalanceOrg) || 0;
  const newOrg = Number(row.newbalanceOrig) || 0;
  const ratio = oldOrg > 0 ? amount / oldOrg : 0;
  if (oldOrg > 0 && newOrg <= 1)
    reasons.push("the sender's balance becomes zero after the transaction");
  if (ratio >= 0.9)
    reasons.push(`the amount is ${Math.round(ratio * 100)}% of the old balance (near-total sweep)`);
  if (amount >= HIGH_AMOUNT_THRESHOLD)
    reasons.push(`the amount (${amount.toLocaleString()}) is unusually large`);
  if (row.type === "TRANSFER" || row.type === "CASH_OUT")
    reasons.push(`it is a ${row.type}, the type most used for fraud`);
  return reasons;
}
