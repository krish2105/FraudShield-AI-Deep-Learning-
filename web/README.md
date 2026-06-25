# FraudShield AI — React + Tailwind Dashboard

A premium dark-theme fintech dashboard (React + Vite + Tailwind + Recharts) that
visualises the payment-fraud sequence-detection project. It replaces the
Streamlit UI with a faster, fully custom front end.

## How it works

The React app is **static** — it reads one precomputed file,
`web/public/data/dashboard.json`, produced by the Python pipeline:

```
src/export_dashboard_data.py   →   web/public/data/dashboard.json
```

That script reuses the SAME scoring logic as the rest of the project (the real
LSTM if trained, otherwise transparent demo rules). The "Fraud Risk Scoring"
page also scores uploaded CSVs **client-side** in the browser, mirroring the
Python demo rules — so it works with no backend running.

## Run it

From the **project root**:

```bash
# 1. (once) make sample data + export the dashboard JSON
python src/make_sample_data.py
python src/export_dashboard_data.py

# 2. install + start the dashboard
cd web
npm install
npm run dev          # opens http://localhost:5173
```

Production build:

```bash
npm run build        # outputs to web/dist/
npm run preview      # serves the built site
```

## Refreshing the data

Whenever you retrain the model or swap in the real PaySim dataset, re-run:

```bash
python src/export_dashboard_data.py
```

…then refresh the browser. The "Demo mode" chip turns into "Model mode" once a
trained LSTM is detected.

## Pages

Executive Overview · Dataset Explorer · Fraud Risk Scoring · Sequence Analyzer ·
Fraud Pattern Insights · Model Performance · Explainability · Alert Center ·
Business Impact Simulator · Recommendations.

## Stack

- React 18 + React Router (hash routing — works as static files)
- Vite 5 build
- Tailwind CSS 3 (custom navy / electric-blue theme)
- Recharts (charts), PapaParse (CSV), lucide-react (icons)
