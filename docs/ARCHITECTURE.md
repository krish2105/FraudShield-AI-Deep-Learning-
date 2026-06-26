# FraudShield AI — Architecture

This document describes the system as it is **today** (the course prototype) and
the **target architecture** for a corporate-grade MVP. Use it alongside
`IMPLEMENTATION_PLAN.md` (how to get there) and `BRAINSTORM.md` (why / what to add).

---

## 1. Current architecture (as-built)

### 1.1 High-level
```
                         ┌─────────────────────────────────────────┐
                         │              CLIENTS                     │
                         │  React SPA (web/dist)   Streamlit UI     │
                         └───────────────┬─────────────┬───────────┘
                                         │ HTTP/JSON    │ in-process
                                         ▼              ▼
                         ┌─────────────────────────────────────────┐
                         │        FastAPI service (api/main.py)     │
                         │  /status /dashboard /score /score/batch  │
                         │  /dataset /train /health                 │
                         └───────────────┬─────────────────────────┘
                                         │ imports
                                         ▼
                         ┌─────────────────────────────────────────┐
                         │            src/ pipeline                 │
                         │  data_loader → feature_engineering →     │
                         │  preprocessing → sequence_builder →      │
                         │  dl_models (PyTorch) → predict           │
                         │  business_rules · evaluate · export      │
                         └───────────────┬─────────────────────────┘
                                         │ reads / writes
                         ┌───────────────┴─────────────────────────┐
                         │  data/  models/  reports/  (filesystem)  │
                         └─────────────────────────────────────────┘
```

### 1.2 Data → prediction flow
1. **Load** — `data_loader.load_data()` reads `data/paysim.csv`, else falls back
   to `data/sample_transactions.csv`.
2. **Feature engineering** — `feature_engineering.engineer_features()` derives
   balance-change deltas, `amount_to_balance_ratio`, zero/high-amount flags,
   per-customer counts, type encoding, and the two strong PaySim signals
   `errorBalanceOrig` / `errorBalanceDest` (double-entry inconsistencies).
3. **Scale** — `preprocessing` fits a `StandardScaler` (saved to
   `models/scaler.pkl`) and transforms feature columns.
4. **Sequence build** — `sequence_builder.build_padded_sequences()` groups rows
   by `nameOrig`, orders by `step`, and produces masked, zero-padded,
   variable-length windows of up to `SEQUENCE_LENGTH=10`, many-to-one.
5. **Model** — `dl_models` trains/serves PyTorch models; `predict.predict_proba`
   returns a fraud probability for the current transaction.
6. **Business mapping** — `business_rules` maps probability → risk band
   (Low/Medium/High) → recommended action, and provides the transparent
   `demo_score` fallback.
7. **Serve** — API returns JSON; React/Streamlit render KPIs, charts, scoring.

### 1.3 Model toolkit (`src/dl_models.py`)
| Model | Role | Architecture |
|-------|------|--------------|
| `DenseBaseline` | order-blind benchmark | Flatten → 64 ReLU → Drop → 32 ReLU → logit |
| `LSTMClassifier` (hero) | temporal/behavioural fraud | pack_padded → LSTM(64) → Drop → 32 ReLU → logit |
| `GRUClassifier` | lighter recurrent variant | pack_padded → GRU(64) → … → logit |
| `CNN1DClassifier` | local "spike-then-drain" motifs | Conv1d×2 → masked mean-pool → 32 ReLU → logit |
| `SequenceAutoencoder` | unsupervised novel-fraud | encoder/decoder on current step; high recon error = anomaly |

- **Loss:** binary focal loss (γ=2.0) + pos_weight (capped 25) for imbalance.
- **Optimizer:** Adam, lr 1e-3, 15 epochs, batch 256.
- **Selection:** primary model chosen by best **PR-AUC**; recall is the
  operational priority. Persisted in `models/inference_artifacts.json`.

### 1.4 Persistence (filesystem, no DB today)
- `models/*.pt` — checkpoints `{name, seq_len, n_features, state_dict}`.
- `models/scaler.pkl`, `models/feature_columns.pkl` — preprocessing artifacts.
- `models/inference_artifacts.json` — primary model name, AE threshold.
- `reports/metrics.json`, `model_comparison.csv`, `curves.json` — evaluation.

### 1.5 Resilience properties (keep these)
- Always-runs: model/scaler missing → demo rules; data missing → sample.
- Stateless API except an in-memory payload cache + a training lock/flag.
- Background retraining via a daemon thread (`/api/train`).

---

## 2. Target architecture (corporate MVP)

The jump from "runs on a laptop" to "corporate MVP" is about **data scale,
real-time serving, persistence, observability, security, and MLOps**.

### 2.1 Target high-level
```
        Clients (Web SPA, Mobile, Partner APIs)
                       │  HTTPS + OAuth2/JWT
                       ▼
              ┌──────────────────┐
              │   API Gateway    │  rate-limit, authn/z, WAF
              └────────┬─────────┘
                       ▼
   ┌──────────────────────────────────────────────────┐
   │      Scoring service (FastAPI, stateless, x-N)    │
   │  /score (p99 < 100ms)  ── feature lookup ──┐      │
   └───────┬───────────────────────────┬────────┘      │
           │                           │               │
           ▼                           ▼               ▼
   ┌──────────────┐         ┌────────────────┐  ┌──────────────┐
   │ Feature Store│         │ Model Registry │  │  Event bus   │
   │ (online: Redis│        │ (MLflow + S3)  │  │ (Kafka/SQS)  │
   │  offline: DWH)│        └────────────────┘  └──────┬───────┘
   └──────────────┘                                    │
           ▲                                            ▼
   ┌───────┴────────┐   ┌──────────────┐      ┌──────────────────┐
   │  Transactions  │   │  Case mgmt / │      │ Async pipelines: │
   │  DB (Postgres) │   │ analyst UI   │      │ retrain, drift,  │
   └────────────────┘   └──────────────┘      │ batch scoring    │
                                              └──────────────────┘
   Cross-cutting: OpenTelemetry tracing, Prometheus/Grafana metrics,
   structured audit logs, CI/CD, IaC (Terraform), secrets manager.
```

### 2.2 Component upgrades vs today
| Concern | Today | Corporate MVP target |
|---------|-------|----------------------|
| Data | CSV files | Postgres (txns) + columnar DWH (training) + object store (raw) |
| Features | Recomputed per request | **Feature store** (online Redis for low-latency, offline for training) — solves train/serve skew |
| Model store | `.pt` files in repo | **Model registry** (MLflow) with versions, stages, lineage |
| Serving | In-process import | Stateless scoring service behind gateway; model loaded from registry; warm cache |
| Retraining | Daemon thread | Orchestrated pipeline (Airflow/Prefect) on schedule + drift trigger |
| Auth | None | OAuth2/JWT, RBAC (analyst vs admin), API keys for partners |
| Observability | `log()` to stdout | OpenTelemetry traces, Prometheus metrics, dashboards, alerting |
| Audit | None | Immutable audit log of every score + decision (compliance) |
| Deploy | Manual | Docker + CI/CD + IaC; blue/green or canary |
| Config | `config.py` | Env-driven config + secrets manager; per-env settings |
| Tests | Minimal | Unit + integration + data-contract + model-quality gates in CI |

### 2.3 Real-time scoring path (target)
1. Transaction event hits gateway → scoring service.
2. Service fetches the customer's recent feature window from the **online
   feature store** (precomputed, not recomputed) → p99 lookup in single-digit ms.
3. Loads the active model version from the **registry cache**.
4. Returns probability + band + action + a request id for audit.
5. Emits a scoring event to the **event bus** → audit log, monitoring, and
   the analyst case-management queue for Medium/High risk.

### 2.4 Feedback & MLOps loop (target)
```
score → analyst decision (confirm/clear) → labeled outcome →
feature store + label store → scheduled/drift-triggered retrain →
shadow eval vs current champion → promote if better (PR-AUC, recall@precision) →
canary → full rollout → monitor drift → repeat
```

### 2.5 Non-functional targets (proposed SLOs)
- Scoring latency: p99 < 100 ms (online), batch throughput ≥ 10k txn/s.
- Availability: 99.9% for the scoring path.
- Model: recall ≥ X% at precision ≥ Y% on a *temporal* holdout (set real targets
  once trained on full PaySim — see `BRAINSTORM.md`).
- Auditability: 100% of decisions logged immutably with model version + features.

---

## 3. Key architectural decisions (ADR-style summary)
- **PyTorch over TensorFlow** — TF segfaults on the dev stack; architectures are
  identical. Revisit only if deploy target needs TF Serving.
- **Sequence many-to-one with masking** — most PaySim accounts have few txns;
  variable-length packed sequences handle this honestly instead of dropping data.
- **PR-AUC for model selection** — accuracy is misleading at <1% fraud.
- **Graceful degradation by design** — demo rules + sample data guarantee a
  always-on demo; keep this even in production as a circuit-breaker fallback.
- **Filesystem persistence (today)** — fine for a course prototype; the single
  biggest lever toward "corporate" is replacing this with DB + feature store +
  model registry (see plan Phase 2–3).
