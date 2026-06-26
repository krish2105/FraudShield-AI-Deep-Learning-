# CLAUDE.md — FraudShield AI

Guidance for AI agents (and humans) working in this repo. Read this first.

## What this project is
FraudShield AI is a **payment-fraud sequence-detection** system built for the
MAIB Sept-25 Deep Learning course (Term 3). The hero model is an **LSTM/RNN**
that scores a transaction in the context of the customer's recent history,
returns a fraud probability, maps it to a risk band, and recommends a business
action (Approve / Review / Block).

It is a **decision-support prototype**, not a deployed bank system. The model
recommends; a human decides on high-impact cases.

## Tech stack (do not "upgrade" without reason)
- **ML:** PyTorch (NOT TensorFlow — TF segfaults on Apple-Silicon + Python 3.13 +
  NumPy 2.x; this is deliberate and documented in `src/dl_models.py`).
- **Backend:** FastAPI + Uvicorn (`api/main.py`).
- **Primary UI:** React + Vite + Tailwind + Recharts (`web/`). Built `web/dist`
  is served by FastAPI at `/`.
- **Alt UI:** Streamlit, 10 pages (`app/`).
- **Deck:** PptxGenJS (`presentation/generate_pptx.js`, Node).

## Repository map
```
src/                Core Python pipeline (data → features → sequences → models)
  config.py         SINGLE SOURCE OF TRUTH: paths, hyperparams, features, thresholds
  data_loader.py    Loads paysim.csv or falls back to sample_transactions.csv
  feature_engineering.py   Engineered features (balance errors, ratios, flags)
  preprocessing.py  Scaler fit/transform (StandardScaler -> scaler.pkl)
  sequence_builder.py      Builds masked, padded, variable-length sequences per account
  dl_models.py      All 5 model classes + train/predict/save/load (PyTorch)
  train_all.py      Trains every model, picks primary by PR-AUC, writes reports
  train_lstm.py / train_dense_nn.py   Single-model helpers
  predict.py        Inference for API + dashboard; falls back to demo rules
  business_rules.py Risk bands, recommended actions, transparent demo_score
  evaluate_model.py Metrics + confusion matrix + curves
  export_dashboard_data.py  Builds the dashboard JSON payload/snapshot
  utils.py          Logging, seeds, JSON read/write
api/main.py         FastAPI: /status /dashboard /score /score/batch /dataset /train
app/                Streamlit dashboard (streamlit_app.py + pages/)
web/                React app (src/pages, src/components, src/lib/api.js)
models/             Trained .pt checkpoints + scaler.pkl + inference_artifacts.json
reports/            metrics.json, model_comparison.csv, curves.json
data/               paysim.csv (real slot), sample_transactions.csv (synthetic)
notebooks/          Payment_Fraud_LSTM_Complete.ipynb (full pipeline walkthrough)
presentation/       PptxGenJS deck generator + speaker script
docs/               Architecture, implementation plan, corporate roadmap
```

## How to run (local)
```bash
# Backend API (also serves the built React app at http://localhost:8000)
uvicorn api.main:app --reload --port 8000

# Streamlit alt UI
streamlit run app/streamlit_app.py --server.port 8501

# React dev server (hot reload, talks to API on :8000)
cd web && npm install && npm run dev          # http://localhost:5173

# Rebuild React for FastAPI to serve
cd web && npm run build                        # -> web/dist

# Train / retrain all models
python src/train_all.py

# Generate the PPTX deck
node presentation/generate_pptx.js
```

## Conventions & invariants
- **All paths are relative**, derived from `PROJECT_ROOT` in `config.py`. Never
  hardcode absolute paths.
- `config.py` is the single source of truth. Change hyperparameters, features,
  and thresholds there — not inline.
- Models save as `.pt` checkpoints carrying `{name, seq_len, n_features,
  state_dict}` so `load_model` can reconstruct without external metadata.
- **The system always runs.** Missing model/scaler → transparent `demo_score`
  rules with `mode="demo"`. Missing `paysim.csv` → `sample_transactions.csv`.
  Preserve this graceful-degradation behavior in any change.
- Primary model is chosen by **PR-AUC** (correct metric for rare-event fraud),
  not accuracy. Recall is the operational priority.
- Imbalance handling: **focal loss + pos_weight** (capped at 25.0).

## Known reality checks (important — don't overstate results)
- `data/paysim.csv` is currently only ~2,083 rows and is effectively
  synthetic-scale (same size as the sample). It is NOT the full ~6.3M-row PaySim
  dataset.
- `reports/metrics.json` shows LSTM/GRU at perfect 1.0 on a **417-row test set
  with 5 fraud cases**. This is too small to be meaningful — perfect scores are
  an artifact of tiny, easy data, not proof of a production model. When writing
  copy or slides, frame metrics honestly and point to the corporate roadmap in
  `docs/BRAINSTORM.md` for the path to credible evaluation.

## When making changes
- Keep the demo-mode fallback intact.
- If you touch features, update `FEATURE_COLUMNS` in `config.py` AND retrain
  (the saved `scaler.pkl` / `feature_columns.pkl` must match).
- After model changes, run `python src/train_all.py` so `models/` and `reports/`
  stay consistent, then refresh the dashboards.
- Don't commit large data or model binaries unless intended; check `.gitignore`.

## Roadmap
See `docs/IMPLEMENTATION_PLAN.md`, `docs/ARCHITECTURE.md`, and
`docs/BRAINSTORM.md` for the path from course prototype to corporate-grade MVP.
