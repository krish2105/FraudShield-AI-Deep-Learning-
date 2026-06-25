# FraudShield AI — Slide Content (16 slides)

Short on-screen bullets only. Full narration lives in the `.pptx` speaker
notes (Presenter View) and in `speaker_script.md`.

Theme: dark navy · electric blue · white · light gray. Premium fintech /
C-level style. 16:9.

---

### Slide 1 — Title
- **FraudShield AI: Payment Fraud Sequence Detection using LSTM / RNN**
- Deep Learning Project — MAIB Sept 25 · Term 3
- Group: Krishna Mathur · Yash Petkar · Atharva Soundankar · __________

### Slide 2 — Executive Summary
- Detect fraud using transaction **behaviour sequences**
- **LSTM** learns suspicious payment patterns
- Output a **fraud risk score** + a **business action**

### Slide 3 — Business Problem
- Sudden large transfers
- Rapid cash-outs
- Balance draining to zero
- Suspicious transaction sequences
- High manual investigation cost

### Slide 4 — Why Fraud Detection Matters
- Financial loss
- Customer trust
- Regulatory risk
- Operational workload
- Reputation damage

### Slide 5 — Limits of Rule-Based Systems
- Example rule: `IF amount > 10,000 THEN block`
- Static rules · too many false alerts
- Fraudsters bypass fixed limits
- No sequence memory

### Slide 6 — Why Deep Learning & LSTM
- Normal ML sees **one** transaction
- LSTM sees a **sequence** of transactions
- LSTM **remembers** past behaviour
- Normal: 100 → 150 → 120 → 90
- Suspicious: 100 → 120 → 9,000 → 9,500 → balance 0

### Slide 7 — Dataset Overview
- step, type, amount
- nameOrig, oldbalanceOrg, newbalanceOrig
- nameDest, oldbalanceDest, newbalanceDest
- isFraud (label)
- PaySim is synthetic → final metrics use real `data/paysim.csv`

### Slide 8 — Feature Engineering
- origin_balance_change
- destination_balance_change
- amount_to_balance_ratio
- zero_balance_flag
- high_amount_flag
- transaction_count_by_customer
- encoded transaction type

### Slide 9 — Sequence Creation Logic
- Transactions: T1 → T2 → T3 → T4 → T5 → T6
- Input to LSTM: T1 … T5
- Prediction: is T6 fraud?
- Shape: samples × sequence_length × features

### Slide 10 — Full System Architecture
- Transaction Data → Cleaning → Feature Engineering →
  Sequence Builder → LSTM Model → Fraud Score → Dashboard → Business Action

### Slide 11 — LSTM Model Architecture
- Input (sequence × features)
- LSTM 64 units → Dropout 0.3 → Dense 32 ReLU → Sigmoid
- Loss: binary cross-entropy · Adam · class weights

### Slide 12 — Model Evaluation Plan
- Accuracy · Precision · **Recall** · F1
- ROC-AUC · PR-AUC · Confusion matrix
- Recall matters most — missing real fraud is costly

### Slide 13 — FraudShield AI Dashboard
1. Executive Overview
2. Dataset Explorer
3. Fraud Risk Scoring
4. Customer Sequence Analyzer
5. Fraud Pattern Insights
6. Model Performance
7. Explainability Panel
8. Alert Center
9. Business Impact Simulator
10. Recommendations

### Slide 14 — Business Impact
- Reduce fraud loss
- Detect suspicious behaviour early
- Reduce manual review workload
- Improve customer trust
- Prioritise high-risk transactions

### Slide 15 — Limitations & Ethics
- PaySim is synthetic; real bank data is private
- Fraud patterns change (drift)
- False positives affect genuine customers
- Human-in-the-loop review
- Data privacy matters

### Slide 16 — Future Scope & Conclusion
- Real-time fraud API
- OTP / SMS integration
- Analyst feedback loop
- Explainable AI (SHAP)
- Cloud deployment + auto-retraining
- **Conclusion:** sequence → score → action, with a premium dashboard
