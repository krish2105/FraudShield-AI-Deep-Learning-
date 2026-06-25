// Small formatting helpers shared across pages.

export function formatCurrency(value, symbol = "$") {
  const v = Number(value) || 0;
  const a = Math.abs(v);
  if (a >= 1e9) return `${symbol}${(v / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `${symbol}${(v / 1e6).toFixed(2)}M`;
  if (a >= 1e3) return `${symbol}${(v / 1e3).toFixed(1)}K`;
  return `${symbol}${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export function formatNumber(value) {
  return (Number(value) || 0).toLocaleString();
}

export function formatPct(value, digits = 1) {
  return `${(Number(value) || 0).toFixed(digits)}%`;
}

// Probability (0..1) -> "73%"
export function probToPct(p, digits = 0) {
  return `${(Number(p) * 100).toFixed(digits)}%`;
}
