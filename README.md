# 🛡️ FraudShield AI — Payment Fraud Sequence Detection using LSTM/RNN

> **Deep Learning Project — MAIB Sept 25 · Term 3**
> Krishna Mathur · Yash Petkar · Atharva Soundankar · __________

A real-life fintech project: an **LSTM/RNN** model detects payment fraud by
analysing a customer's **sequence of transactions**, then returns a **fraud
risk score** and a **recommended business action** — all wrapped in a premium
Streamlit dashboard and a C-level PowerPoint deck.

> ⚠️ **Data honesty:** the repo ships with **synthetic sample data** so
> everything runs out of the box. Any metrics shown before training are
> placeholders that say **"Update after running on real dataset."** Drop the
> real PaySim file at `data/paysim.csv` and re-run the notebook for final
> results.

---

## 1. Project Overview
FraudShield AI scores each payment **before approval**. Instead of judging one
transaction in isolation, it reads the customer's recent history as a sequence
and predicts whether the **next** transaction is fraud. The score maps to a
clear action so a bank, wallet or payment gateway can act in real time.

## 2. Business Problem
Digital payment fraud is fast and hides in behaviour: sudden large transfers,
rapid cash-outs, and balances draining to zero. Manual investigation is
expensive and slow. The business needs **automatic, sequence-aware** detection.

## 3. Why LSTM / RNN
| Normal ML | LSTM / RNN |
|-----------|------------|
| Sees **one** transaction | Reads a **sequence** in order |
| No memory of history | **Remembers** past behaviour |
| Misses behavioural breaks | Flags a sudden spike after a calm history |

Example — normal: `100 → 150 → 120 → 90`; suspicious:
`100 → 120 → 9,000 → 9,500 → balance 0`.

## 4. Dataset
The **PaySim** mobile-money dataset. Columns:

`step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig, nameDest,
oldbalanceDest, newbalanceDest, isFraud, isFlaggedFraud`

See [`data/README_DATA.md`](data/README_DATA.md) for details and the download
link. If `data/paysim.csv` is missing, the project uses
`data/sample_transactions.csv` (synthetic, demo only).

## 5. Folder Structure
```
payment_fraud_lstm_project/
├── data/                 sample data + data docs (real paysim.csv goes here)
├── notebooks/            Payment_Fraud_LSTM_Complete.ipynb  (full pipeline)
├── app/                  Streamlit dashboard (streamlit_app.py + 10 pages)
│   ├── pages/            one file per dashboard page
│   └── assets/style.css  premium fintech theme
├── src/                  modular, tested Python (data → features → model)
├── models/               saved .keras models + scaler (after training)
├── reports/              metrics.json + model_comparison.csv
├── presentation/         PptxGenJS generator + .pptx + scripts
├── screenshots/          add your dashboard screenshots here
├── README.md / run_project.md / requirements.txt / package.json / .gitignore
```

## 6. How to Install
```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
python src/make_sample_data.py
```

## 7. How to Run the Notebook
```bash
jupyter notebook notebooks/Payment_Fraud_LSTM_Complete.ipynb
```
Run all cells top to bottom (load → EDA → features → sequences → train →
evaluate → save).

## 8. How to Train the Model
Training happens inside the notebook (sections 11–15). It saves
`models/lstm_fraud_model.keras`, the Dense baseline, the scaler, and writes
`reports/metrics.json` + `reports/model_comparison.csv`. You can also call the
`src/train_lstm.py` and `src/train_dense_nn.py` helpers directly.

## 9. How to Run the Dashboard

**Primary UI — React + Tailwind, backed by a FastAPI service:**

```bash
# Terminal 1 — backend (live scoring, dataset upload, retrain)
python src/export_dashboard_data.py     # build web/public/data/dashboard.json
uvicorn api.main:app --port 8000

# Terminal 2 — React app
cd web && npm install && npm run dev     # http://localhost:5173
```

A premium dark dashboard (Vite + React + Tailwind + Recharts). With the API up
you get **live single-transaction scoring**, a **Dataset & Model Manager** (upload
the real PaySim CSV, retrain), and functional status chips. Without it, the app
still runs from the precomputed JSON snapshot. See [`web/README.md`](web/README.md)
and the API endpoints in [`api/main.py`](api/main.py).

**Alternative UI — Streamlit:** `streamlit run app/streamlit_app.py`

Both UIs run in **demo mode** (transparent rules) until the models are trained,
then switch to real **LSTM** scoring. Retrain anytime with `python src/train_all.py`
(or the in-app manager), then refresh.

## 10. How to Generate the PPT
```bash
npm install
node presentation/generate_pptx.js      # or: npm run generate:ppt
```
Creates `presentation/FraudShield_AI_Payment_Fraud_LSTM.pptx` with **speaker
notes** on every slide (open in PowerPoint → Presenter View).

## 11. Dashboard Tabs
| Page | What it shows |
|------|---------------|
| **Executive Overview** | KPIs, amount at risk, fraud & volume trends |
| **Dataset Explorer** | preview, column docs, missing values, distributions, filters |
| **Fraud Risk Scoring** | upload CSV → fraud probability, risk band, action, export |
| **Customer Sequence Analyzer** | a customer's last 10 txns, timeline, why it's risky |
| **Fraud Pattern Insights** | fraud by type / amount / time, balance-draining txns |
| **Model Performance** | metrics from `reports/`, confusion matrix, metric meanings |
| **Explainability Panel** | plain-English reasons + approximate feature importance |
| **Alert Center** | high-risk queue, recommended action, CSV export |
| **Business Impact Simulator** | loss prevented, review cost, net savings |
| **Recommendations** | guidance, limitations, ethics, future scope |

## 12. Model Architecture (PyTorch — a toolkit matched to fraud)

| Model | Role | Shape |
|-------|------|-------|
| **Dense baseline** | order-blind benchmark | `Flatten → 64 ReLU → Drop 0.3 → 32 ReLU → Sigmoid` |
| **LSTM** (hero) | behavioural/temporal fraud | `Masked pack → LSTM 64 → Drop 0.3 → 32 ReLU → Sigmoid` |
| **GRU** | lighter recurrent variant | `Masked pack → GRU 64 → … → Sigmoid` |
| **1D-CNN** | local "spike-then-drain" motifs | `Conv1d×2 → masked mean-pool → 32 ReLU → Sigmoid` |
| **Autoencoder** | unsupervised novel-fraud detector | trained on genuine only; flags high reconstruction error |

Sequences are **masked, variable-length, many-to-one**: score the current
transaction using up to `SEQUENCE_LENGTH` preceding transactions of the same
account (zero-padded + packed), so it works on the real PaySim data where most
accounts have few transactions. Loss = **focal loss + pos-weight** for the
extreme imbalance · optimizer = Adam. We pick the **primary model by best
PR-AUC** (the right metric for rare fraud); recall is the operational priority.

> **Framework:** PyTorch (not TensorFlow — TF segfaults on Apple-Silicon /
> Python 3.13 / NumPy 2). The architectures are unchanged.

**Fraud risk rules:**
| Probability | Band | Action |
|-------------|------|--------|
| 0.00 – 0.30 | Low | Approve |
| 0.31 – 0.70 | Medium | Manual Review / OTP |
| 0.71 – 1.00 | High | Block / Alert Fraud Team |

## 13. Business Impact
Reduce fraud loss · detect suspicious behaviour early · cut manual review
workload · improve customer trust · prioritise high-risk transactions. The
Business Impact Simulator estimates net savings from your own assumptions.

## 14. Limitations
- PaySim is **synthetic**; real bank data is private and behaves differently.
- Fraud patterns **drift** over time — retraining is required.
- **False positives** inconvenience genuine customers.
- The shipped sample is small and for demonstration only.

## 15. Future Improvements
Real-time fraud API · OTP/SMS step-up · analyst feedback loop · explainable AI
(SHAP) · cloud deployment with automatic retraining.

## 16. Group Member Roles
| Member | Focus |
|--------|-------|
| **Krishna Mathur** | Intro, business problem, dashboard, conclusion |
| **Yash Petkar** | Dataset, preprocessing, feature engineering |
| **Atharva Soundankar** | LSTM architecture, model training, evaluation |
| **__________** | Limitations, ethics, future scope |

---

*FraudShield AI is a decision-support tool. The model recommends; a human
decides on high-impact cases. Built for the MAIB Sept 25 Deep Learning course.*
