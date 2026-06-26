# FraudShield AI — Brainstorm & Improvement Backlog

A wide-net brainstorm for turning the course prototype into a **corporate-grade
MVP**. Organized by theme. Each item notes **why it matters** and rough
**impact**. Pair this with `IMPLEMENTATION_PLAN.md` (sequencing) and
`ARCHITECTURE.md` (target design).

> **Read this first — the single most important truth about the project today:**
> The "real" results are not real yet. `data/paysim.csv` is ~2,083 rows (sample
> scale) and `reports/metrics.json` shows LSTM/GRU at **perfect 1.0** on a
> 417-row test set with **5 fraud cases**. Perfect scores on tiny data are a
> *red flag*, not an achievement. **The #1 credibility upgrade is full-dataset,
> temporally-split, calibrated evaluation.** Everything else is secondary to
> this for a corporate audience.

---

## 1. Model & ML quality (highest leverage)

### 1.1 Evaluation you can defend 🔴
- Train on the **full PaySim** (~6.3M rows), not the 2k sample.
- **Temporal split** (past→future), never random shuffle — fraud models leak
  badly with random splits.
- Report **PR-AUC, recall@precision, precision@recall**, and a **cost-weighted**
  score (a missed fraud costs far more than a false alarm).
- **Probability calibration** (isotonic/Platt) so 0.3/0.7 bands are meaningful.
- **Confidence intervals** via multiple seeds / bootstrapping. Kill the "1.0".

### 1.2 Better imbalance handling 🟡
- Compare focal loss vs class-weighting vs SMOTE/ADASYN (on the sequence level).
- **Threshold from a cost curve**, tuned to the bank's false-positive tolerance.
- Per-segment thresholds (by transaction type / amount band).

### 1.3 Stronger / modern models 🟡
- **Attention / Transformer encoder** over the transaction sequence — current
  SOTA for sequential fraud; compare against the LSTM hero honestly.
- **Gradient-boosted trees (XGBoost/LightGBM)** on engineered features as a
  strong tabular baseline — often beats deep nets on tabular fraud; include it
  so the LSTM's value is proven, not assumed.
- **Graph features / GNN**: model the `nameOrig → nameDest` money-movement graph
  to catch mule networks and fan-in/fan-out laundering patterns.
- **Ensemble / stacking**: combine sequence model + tree + autoencoder anomaly
  score into a meta-scorer.

### 1.4 Features 🟡
- **Velocity features**: count/sum of transfers in last 1h/24h/7d per account.
- **Recipient risk**: how many distinct senders a `nameDest` receives from
  (mule indicator), first-time-recipient flag.
- **Time-of-day / burstiness** signals.
- **Entity embeddings** for transaction type and (hashed) account ids.
- Keep `errorBalanceOrig/Dest` — they're the strongest PaySim signals.

### 1.5 Drift & monitoring 🔴
- **Data drift** (PSI/KL on feature distributions) and **concept drift**
  (rolling PR-AUC) detection → trigger retrain.
- **Score-distribution monitoring** to catch model rot before metrics tank.

---

## 2. Explainability & trust 🔴
- **Per-decision explanations**: SHAP (for tree/tabular) or Integrated Gradients /
  attention weights (for the sequence model), surfaced in the UI as "top reasons."
- **Model card** documenting intended use, training data, metrics, limitations,
  and fairness considerations.
- **Reason codes** mapped to plain English ("sudden 90× spike vs 30-day median",
  "balance drained to zero", "first transfer to this recipient").
- **Counterfactuals**: "this would be Low risk if amount were under X."

---

## 3. Data & persistence 🔴
- Move from CSV → **Postgres** (transactions, scores, decisions, audit).
- **Feature store** (online Redis + offline) to eliminate train/serve skew —
  today features are recomputed at request time, which is both slow and risky.
- **Object storage** for raw data + model artifacts.
- **Data contracts / schema validation** on ingestion (Great Expectations or
  Pandera) so bad data is rejected, not silently scored.

---

## 4. Real-time serving & API 🔴
- **AuthN/Z** (OAuth2/JWT, partner API keys, RBAC), **rate limiting**, strict
  **input validation**.
- **Versioned API** (`/v1`), idempotency keys, request ids.
- **Latency SLO** p99 < 100 ms with a warm model cache; **load test** to prove it.
- **Streaming ingestion** (Kafka) for true real-time scoring at scale.
- Keep the **demo-mode fallback** as an explicit circuit breaker.

---

## 5. MLOps & deployment 🔴
- **MLflow** registry (champion/challenger, lineage) replacing the JSON pointer.
- **Orchestrated retraining** (Prefect/Airflow), scheduled + drift-triggered.
- **Shadow + canary** rollout with automatic rollback on metric regression.
- **Dockerize** everything; `docker-compose` full stack; **CI/CD** with a
  model-quality gate; **Terraform** IaC; staging + prod envs.

---

## 6. Observability, security, compliance 🔴
- **OpenTelemetry tracing**, **Prometheus/Grafana** dashboards, alerting.
- **Immutable audit log** of every score + decision (AML/regulatory need).
- **Secrets manager**; **PII tokenization/hashing**; data-retention policy.
- **Fairness/bias audit** across segments; document in the model card.
- **Penetration test** of the scoring API before any external exposure.

---

## 7. Product & analyst experience 🟡
- **Case-management workflow**: alert queue → assign → investigate → resolve;
  the analyst's verdict becomes a training label (**closes the feedback loop**).
- **Step-up actions** wired to risk bands (OTP/SMS for Medium, block+alert for
  High) with webhooks to email/Slack.
- **Admin console** to edit thresholds, costs, and business rules without code.
- **Investigation view**: customer timeline, money-movement graph, similar past
  cases.
- **Multi-tenancy** if serving multiple banks/partners.
- **Feedback button** so analysts can flag wrong scores → active learning.

---

## 8. Engineering quality (pay down early) 🟡
- **Test suite** (`tests/`): start with `sequence_builder`, `feature_engineering`,
  and the `predict` demo-fallback path; add API integration tests.
- **Type hints + mypy**, **ruff/black**, pre-commit hooks.
- **12-factor config** via `pydantic-settings` + env vars (no hardcoded values).
- **Structured logging** replacing `print`/`log()`.
- **Pinned dependencies** + lockfiles for reproducible builds.

---

## 9. "Wow" demo ideas for the presentation 🟢
- **Live transaction simulator**: a slider/stream that fires transactions and
  shows the risk score updating in real time as a customer's behavior shifts
  from normal → fraudulent (this is the visual that sells the LSTM story).
- **Side-by-side**: single-transaction model vs sequence model on the same
  "100 → 120 → 9,000 → 9,500 → balance 0" pattern, showing the sequence model
  catches what the point model misses.
- **Money-movement graph** animation for a mule network.
- **Business Impact slider**: drag fraud-loss/review-cost assumptions and watch
  net savings recompute live.
- **"What changed" panel**: top 3 reason codes for the current decision.

---

## 10. Honest risks & limitations to state openly
- PaySim is **synthetic**; real bank behavior differs — models will need
  retraining on real data and will drift.
- **False positives** carry real customer cost; the threshold is a business
  trade-off, not a purely technical one.
- A perfect score on a tiny sample means **nothing** — credibility depends on
  full-data, temporally-split, calibrated evaluation (Section 1.1).
- Fraud is **adversarial**: attackers adapt, so detection is a moving target
  requiring monitoring + retraining, not a one-time model.

---

## Priority shortlist (if you only do 5 things)
1. **Full-data, temporal, calibrated evaluation** — kill the fake 1.0. (§1.1)
2. **Postgres + audit log** — persistence and traceability. (§3, §6)
3. **Auth + input validation + versioned API** — secure the scoring path. (§4)
4. **Per-decision explainability (SHAP/IG) in the UI.** (§2)
5. **Docker + CI + model registry (MLflow).** (§5)

These five take the project from "course demo" to "credible corporate MVP."
