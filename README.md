# 🛡️ FraudShield AI — Payment Fraud Sequence Detection (LSTM/RNN)

> **Deep Learning Project — MAIB Sept 25 · Term 3**
> Krishna Mathur · Yash Petkar · Atharva Soundankar · __________

A real-life fintech project: an **LSTM/RNN** model detects payment fraud by
analysing a customer's **sequence of transactions**, then returns a **fraud risk
score** and a **recommended business action** — wrapped in a premium **React**
dashboard (FastAPI-backed), a **Streamlit** alternative UI, and a C-level deck.

> ⚠️ **Data & metrics honesty.** The repo ships with synthetic, sample-scale data
> (`data/sample_transactions.csv`, ~2k rows). The current `reports/metrics.json`
> reflects a *tiny* test set (417 rows / 5 frauds) — perfect scores there are an
> artifact of small data, **not** production-grade evidence. For credible results,
> drop the full **PaySim** dataset at `data/paysim.csv` and retrain. See
> [`docs/BRAINSTORM.md`](docs/BRAINSTORM.md) for the path to defensible metrics.

---

## Quick start

```bash
pip install -r requirements.txt    # install (pinned, reproducible)
./run.sh                           # start API + Streamlit, wait for health, open browser
```

Then open **http://localhost:8000** (React) or **http://localhost:8501** (Streamlit).
Before presenting, prove the demo is healthy:

```bash
python scripts/smoke_test.py       # -> "ALL CHECKS PASSED 🛡️"
```

Common tasks (`make help` for the full list):

```bash
make run          # start everything (= ./run.sh)
make data-large   # generate a ~500k-row synthetic dataset
make train        # train all models (temporal split + calibration)
make test         # run the test suite (16 tests)
make stop         # stop the services
```

> Prefer the manual commands? `uvicorn api.main:app --port 8000` and
> `streamlit run app/streamlit_app.py --server.port 8501` still work.

**Train on the full real dataset:** `python src/download_paysim.py` (needs your
Kaggle credentials) installs the real 6.3M-row PaySim file, then `make train`.
See [`docs/CHANGES.md`](docs/CHANGES.md) for everything that was built.

---

## 1. Project overview
FraudShield AI scores each payment **before approval**. Instead of judging one
transaction in isolation, it reads the customer's recent history as a sequence
and predicts whether the **next** transaction is fraud. The score maps to a clear
action (Approve / Review / Block) so a bank, wallet, or payment gateway can act
in real time.

## 2. Business problem
Digital payment fraud is fast and hides in behaviour: sudden large transfers,
rapid cash-outs, balances draining to zero. Manual investigation is expensive and
slow. The business needs **automatic, sequence-aware** detection.

## 3. Why LSTM / RNN
| Normal ML | LSTM / RNN |
|-----------|------------|
| Sees **one** transaction | Reads a **sequence** in order |
| No memory of history | **Remembers** past behaviour |
| Misses behavioural breaks | Flags a sudden spike after a calm history |

Example — normal: `100 → 150 → 120 → 90`; suspicious:
`100 → 120 → 9,000 → 9,500 → balance 0`.

## 4. Dataset
The **PaySim** mobile-money dataset. Columns: `step, type, amount, nameOrig,
oldbalanceOrg, newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest, isFraud,
isFlaggedFraud`. If `data/paysim.csv` is missing, the project falls back to
`data/sample_transactions.csv` (synthetic, demo only). See
[`data/README_DATA.md`](data/README_DATA.md).

## 5. Architecture (toolkit matched to fraud) — **PyTorch**
| Model | Role | Shape |
|-------|------|-------|
| **Dense baseline** | order-blind benchmark | `Flatten → 64 → 32 → logit` |
| **LSTM** (hero) | behavioural/temporal fraud | `pack → LSTM 64 → 32 → logit` |
| **GRU** | lighter recurrent variant | `pack → GRU 64 → … → logit` |
| **1D-CNN** | local "spike-then-drain" motifs | `Conv1d×2 → mean-pool → logit` |
| **Autoencoder** | unsupervised novel-fraud | genuine-only; high recon error = anomaly |

Sequences are **masked, variable-length, many-to-one**: score the current
transaction using up to `SEQUENCE_LENGTH=10` preceding transactions of the same
account (zero-padded + packed). Loss = **focal loss + pos-weight** for the
extreme imbalance; optimizer = Adam. The **primary model is chosen by best
PR-AUC** (the right metric for rare fraud); recall is the operational priority.

> **Framework note:** PyTorch, not TensorFlow — TF segfaults on Apple-Silicon /
> Python 3.13 / NumPy 2. The architectures are unchanged. See
> [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system design and
> the corporate-MVP target architecture.

**Fraud risk rules:**
| Probability | Band | Action |
|-------------|------|--------|
| 0.00 – 0.30 | Low | Approve |
| 0.31 – 0.70 | Medium | Manual Review / OTP |
| 0.71 – 1.00 | High | Block / Alert Fraud Team |

## 6. Folder structure
```
FraudiShield_dl/
├── api/            FastAPI service (live scoring, dataset upload, retrain)
├── app/            Streamlit dashboard (streamlit_app.py + 10 pages)
├── web/            React + Vite + Tailwind app (served from web/dist by FastAPI)
├── src/            Core pipeline: data → features → sequences → models → predict
├── models/         Trained .pt checkpoints + scaler.pkl + inference_artifacts.json
├── reports/        metrics.json, model_comparison.csv, curves.json
├── data/           paysim.csv (real slot) + sample_transactions.csv (synthetic)
├── notebooks/      Payment_Fraud_LSTM_Complete.ipynb (full pipeline walkthrough)
├── presentation/   PptxGenJS deck generator + speaker script
├── docs/           ARCHITECTURE.md · IMPLEMENTATION_PLAN.md · BRAINSTORM.md
├── CLAUDE.md       Guidance for AI agents / contributors (read first)
└── README.md / requirements.txt / package.json
```

## 7. How to run

### Backend API + React (primary)
```bash
uvicorn api.main:app --reload --port 8000      # serves web/dist at /
```
To develop the React app with hot reload:
```bash
cd web && npm install && npm run dev           # http://localhost:5173 (calls API :8000)
cd web && npm run build                         # rebuild web/dist for FastAPI to serve
```

### Streamlit (alternative UI)
```bash
streamlit run app/streamlit_app.py --server.port 8501
```

Both UIs run in **demo mode** (transparent rules) until models are trained, then
switch to real **LSTM** scoring. The system **always runs**: missing model →
demo rules; missing `paysim.csv` → sample data.

## 8. How to train
```bash
python src/train_all.py        # trains all 5 models, picks primary by PR-AUC,
                               # writes models/*.pt + reports/metrics.json
```
Or use the in-app **Dataset & Model Manager** (upload a PaySim CSV → retrain).
The full pipeline is also walked through in
`notebooks/Payment_Fraud_LSTM_Complete.ipynb`.

## 9. Generate the presentation
```bash
npm install
node presentation/generate_pptx.js      # or: npm run generate:ppt
```
Creates `presentation/FraudShield_AI_Payment_Fraud_LSTM.pptx` with speaker notes
(open in PowerPoint → Presenter View).

## 10. API endpoints (`api/main.py`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/status` | mode/source/primary, training state, thresholds |
| GET | `/api/dashboard` | full dashboard payload (aggregates + curves) |
| POST | `/api/score` | live single-transaction scoring (+ history) |
| POST | `/api/score/batch` | score a list of transactions |
| POST | `/api/dataset` | upload a PaySim CSV, validate, refresh |
| POST | `/api/train` | retrain all models in the background |
| GET | `/api/health` | liveness check |

Interactive docs at **http://localhost:8000/docs**.

## 11. Dashboard pages
Executive Overview · Dataset Explorer · Fraud Risk Scoring · Customer Sequence
Analyzer · Fraud Pattern Insights · Model Performance · Explainability · Alert
Center · Business Impact Simulator · Recommendations.

## 12. Business impact
Reduce fraud loss · detect suspicious behaviour early · cut manual-review
workload · improve customer trust · prioritise high-risk transactions. The
Business Impact Simulator estimates net savings from your own assumptions.

## 13. Limitations
- PaySim is **synthetic**; real bank data is private and behaves differently.
- Fraud patterns **drift** — retraining is required.
- **False positives** inconvenience genuine customers (a business trade-off).
- The shipped sample is small and for demonstration only; see the honesty note
  at the top and [`docs/BRAINSTORM.md`](docs/BRAINSTORM.md) §1.1.

## 14. Roadmap — from prototype to corporate MVP
This repo is a course prototype with a clear path to a production-grade MVP:
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — as-built + target architecture.
- [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) — phased plan.
- [`docs/BRAINSTORM.md`](docs/BRAINSTORM.md) — improvement backlog + priorities.

**Top 5 upgrades:** full-data temporal calibrated evaluation · Postgres + audit
log · auth + input validation + versioned API · per-decision explainability
(SHAP/IG) · Docker + CI + MLflow registry.

## 15. Group member roles
| Member | Focus |
|--------|-------|
| **Krishna Mathur** | Intro, business problem, dashboard, conclusion |
| **Yash Petkar** | Dataset, preprocessing, feature engineering |
| **Atharva Soundankar** | LSTM architecture, model training, evaluation |
| **__________** | Limitations, ethics, future scope |

---

*FraudShield AI is a decision-support tool. The model recommends; a human decides
on high-impact cases. Built for the MAIB Sept 25 Deep Learning course.*
