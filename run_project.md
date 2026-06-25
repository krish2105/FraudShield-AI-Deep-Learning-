# ▶ Run FraudShield AI — Step by Step (Beginner Friendly)

Follow these steps in order. Copy-paste each command into your terminal.
Everything works even **without** the real dataset or a trained model.

---

## 0. Open a terminal in the project folder

```bash
cd payment_fraud_lstm_project   # the folder that contains this file
```

## 1. Create and activate a virtual environment

```bash
python -m venv .venv
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

## 2. Install the Python packages

```bash
pip install -r requirements.txt
```
(First install can take a few minutes — TensorFlow is large.)

## 3. Create the sample dataset

```bash
python src/make_sample_data.py
```
This writes `data/sample_transactions.csv` (demo data only).

## 4. (Optional) Train the models in the notebook

```bash
jupyter notebook notebooks/Payment_Fraud_LSTM_Complete.ipynb
```
Run all cells (top to bottom). This trains the Dense baseline + LSTM and saves:
- `models/lstm_fraud_model.keras`
- `models/dense_nn_baseline.keras`
- `models/scaler.pkl`, `models/feature_columns.pkl`
- `reports/metrics.json`, `reports/model_comparison.csv`

> Skip this step if you just want to see the dashboard — it runs in
> **demo mode** without a trained model.

## 4b. Train the deep-learning models (PyTorch)

```bash
python src/train_all.py
```
Trains Dense, **LSTM**, GRU, 1D-CNN and the Autoencoder, then saves the models
(`models/*.pt`), metrics and evaluation curves (`reports/`). Takes a few seconds
on the sample data. (Running the notebook does the same thing with plots.)

> We use **PyTorch**, not TensorFlow — TF segfaults on Apple-Silicon + Python
> 3.13 + NumPy 2. The architectures (LSTM/RNN) are identical.

## 5. Launch the dashboard (React + the FastAPI backend)

The MVP runs as two processes: a Python API and the React app.

**Terminal 1 — backend API** (live scoring, dataset upload, retrain):
```bash
python src/export_dashboard_data.py          # build the dashboard JSON once
uvicorn api.main:app --port 8000
```

**Terminal 2 — React dashboard:**
```bash
cd web
npm install
npm run dev          # opens http://localhost:5173
```

The web app auto-detects the backend (Vite proxies `/api` → :8000). With the API
running you get the **Demo/Model & Sample/Real chips** (open the manager to
upload the real PaySim CSV or retrain), and **live single-transaction scoring**
on the Fraud Risk Scoring page. Without the backend it still works from the
precomputed JSON snapshot.

**One-port production build** (FastAPI serves the built app too):
```bash
cd web && npm run build && cd ..
uvicorn api.main:app --port 8000      # open http://localhost:8000
```

### Alternative UI — Streamlit
```bash
streamlit run app/streamlit_app.py    # http://localhost:8501
```

## 6. Generate the PowerPoint (needs Node.js)

```bash
npm install
node presentation/generate_pptx.js
# or:  npm run generate:ppt
```
This creates `presentation/FraudShield_AI_Payment_Fraud_LSTM.pptx`
with **speaker notes** (open in PowerPoint → Presenter View).

---

## 🔁 Using the REAL PaySim dataset

1. Download PaySim (Kaggle: "PaySim — Synthetic Financial Datasets For Fraud
   Detection").
2. Rename the CSV to `paysim.csv` and place it in `data/`.
3. Re-run the notebook (step 4). It automatically prefers `data/paysim.csv`.
4. The dashboard and `reports/metrics.json` update with **real** results.

---

## ❓ Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: src` | Run commands from the project root folder. |
| Dashboard says "demo mode" | Train the model (step 4) to enable real scoring. |
| `tensorflow` install fails | Use Python 3.10–3.12; upgrade pip: `pip install -U pip`. |
| `st.navigation` error | Upgrade Streamlit: `pip install -U "streamlit>=1.36"`. |
| Node not found | Install Node.js 18+ from nodejs.org, then retry step 6. |
