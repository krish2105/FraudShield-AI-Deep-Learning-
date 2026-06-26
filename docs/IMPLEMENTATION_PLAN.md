# FraudShield AI — Implementation Plan (Prototype → Corporate MVP)

> **STATUS (implemented & verified):** Phases **0–7 are done** to MVP depth and
> run locally + in Docker. ✅ Phase 0 (launcher, pinned deps, smoke test) ·
> ✅ Phase 1 (full-scale training, temporal split, calibration, fraud metrics) ·
> ✅ Phase 2 (SQLite/Postgres audit persistence) · ✅ Phase 3 (MLflow tracking +
> model registry) · ✅ Phase 4 (auth, validation, request IDs, `/api/v1`) ·
> ✅ Phase 5 (Prometheus `/metrics`, audit trail, structured config) ·
> ✅ Phase 6 (Dockerfile, docker-compose, GitHub Actions CI) ·
> ✅ Phase 7 (explainability, 16 tests, case-decision endpoint).
> **Not done (needs your cloud/credentials):** real PaySim data, cloud deploy,
> Kafka streaming, Terraform, managed feature store. See `docs/CHANGES.md`.


A phased, prioritized roadmap. Each phase has a **goal**, **why it matters**,
concrete **tasks**, and a **definition of done**. Phases are ordered so each one
unlocks the next. You do not need all of them for the course — Phase 0 is the
"make the current project bulletproof for the presentation" phase.

Legend: 🔴 high impact · 🟡 medium · 🟢 polish · ⏱ rough effort.

---

## Phase 0 — Harden the prototype (do before the presentation) 🔴 ⏱ 1–2 days
**Goal:** the existing demo is credible, honest, and never breaks on stage.

- [ ] **Fix the metrics honesty problem.** `reports/metrics.json` shows LSTM = 1.0
      on 417 rows / 5 frauds. Either (a) train on the full PaySim dataset, or
      (b) add a visible "evaluated on a small sample — not production metrics"
      caveat in the UI and slides. *(See Phase 1 for the real fix.)*
- [ ] **Pin dependencies.** Freeze working versions into `requirements.txt`
      (`pip freeze`) and commit `web/package-lock.json`.
- [ ] **Add a one-command launcher.** `make run` / `run.sh` that starts API +
      Streamlit and opens the browser, so the demo is reproducible.
- [ ] **Smoke test.** A script that hits `/api/health`, `/api/status`,
      `/api/score` with a known payload and asserts a sane response.
- [ ] **Screenshots** in `screenshots/` for the deck and README.
- [ ] **README + CLAUDE.md** accurate (this commit).

**Done when:** a fresh clone runs both UIs with documented commands, the demo
works offline, and no claim in the UI/deck overstates the evidence.

---

## Phase 1 — Real data & credible evaluation 🔴 ⏱ 3–5 days
**Goal:** results a corporate reviewer would believe.

- [ ] **Use the full PaySim dataset** (~6.3M rows) instead of the 2k sample.
      Add a downloader/instructions; keep the file out of git (it's large).
- [ ] **Temporal split, not random.** Train on earlier `step`s, test on later —
      fraud detection must be evaluated on the future, never shuffled.
- [ ] **Scope correctly.** Consider `SCOPE_TO_FRAUD_TYPES=True` (fraud only
      occurs in TRANSFER/CASH_OUT in PaySim) and document the choice.
- [ ] **Report the right metrics:** PR-AUC, recall @ fixed precision, precision @
      fixed recall, and a cost-weighted metric (false-negative ≫ false-positive).
- [ ] **Calibration.** Add probability calibration (Platt/isotonic) so the
      0.3/0.7 bands mean something.
- [ ] **Threshold selection from a cost curve**, not hardcoded 0.3/0.7.
- [ ] **Cross-validation / multiple seeds** with mean ± std, so a single lucky
      run can't claim 1.0.

**Done when:** `reports/metrics.json` reflects full-data, temporally-split,
calibrated results with honest numbers and confidence intervals.

---

## Phase 2 — Persistence & data layer 🔴 ⏱ 1 week
**Goal:** replace flat files with a real data backbone.

- [ ] **Postgres** for transactions, scores, decisions, and audit.
- [ ] **SQLAlchemy models + Alembic migrations.**
- [ ] **Score & audit tables:** every prediction stored with request id, model
      version, input features snapshot, probability, band, action, timestamp.
- [ ] **Repository layer** in `src/` so the pipeline reads/writes the DB, not CSVs
      (keep CSV import as an ingestion path).
- [ ] **Object storage** (S3/MinIO) for raw datasets and model artifacts.

**Done when:** scoring a transaction persists an auditable record and the
dashboard reads aggregates from the DB.

---

## Phase 3 — MLOps: registry, feature store, pipelines 🔴 ⏱ 1–2 weeks
**Goal:** models are versioned, reproducible, and retrainable on a schedule.

- [ ] **MLflow** experiment tracking + model registry (champion/challenger
      stages). Replace `inference_artifacts.json` primary-pointer with a registry
      stage lookup.
- [ ] **Feature store** (Feast or a Redis-backed online table) to kill
      train/serve skew — serving reads precomputed features, not recomputed ones.
- [ ] **Orchestrated retraining** (Prefect/Airflow): scheduled + drift-triggered.
- [ ] **Shadow / canary deploy** of a new model before promotion.
- [ ] **Data & model quality gates** that block a bad model from promotion.

**Done when:** a new model can be trained, evaluated, registered, shadow-tested,
and promoted without code changes — all tracked.

---

## Phase 4 — Real-time serving & API hardening 🔴 ⏱ 1 week
**Goal:** the scoring path behaves like a production microservice.

- [ ] **AuthN/Z:** OAuth2/JWT, API keys for partners, RBAC (analyst vs admin).
- [ ] **Rate limiting + input validation** (strict Pydantic schemas, reject bad
      payloads with clear errors).
- [ ] **Idempotency + request ids** on `/score`.
- [ ] **Latency budget:** warm model cache, async I/O, p99 < 100 ms; load test.
- [ ] **Versioned API** (`/v1/...`) and OpenAPI docs published.
- [ ] **Graceful fallback preserved** as an explicit circuit breaker.

**Done when:** the API is authenticated, validated, rate-limited, versioned, and
meets a documented latency SLO under load test.

---

## Phase 5 — Observability, security, compliance 🔴 ⏱ 1 week
**Goal:** you can see, trust, and defend the system.

- [ ] **OpenTelemetry tracing** end-to-end; **Prometheus + Grafana** dashboards
      (latency, throughput, error rate, score distribution, drift).
- [ ] **Alerting** on drift, error spikes, latency breaches.
- [ ] **Immutable audit log** of every decision (compliance/AML requirement).
- [ ] **Secrets manager** (no secrets in code/env files in repo).
- [ ] **PII handling**: hashing/tokenization of account identifiers; data
      retention policy.
- [ ] **Bias & fairness check** + model card documenting intended use & limits.

**Done when:** every decision is traceable and auditable, dashboards are live,
and a security/compliance reviewer has a model card + audit trail.

---

## Phase 6 — Deployment & CI/CD 🟡 ⏱ 1 week
**Goal:** ship reproducibly.

- [ ] **Dockerize** API, web, and a training image; `docker-compose` for local
      full-stack (API + web + Postgres + Redis + MLflow).
- [ ] **CI** (GitHub Actions): lint, type-check, unit/integration tests, build,
      model-quality gate.
- [ ] **CD**: push images, deploy to a cloud target; blue/green or canary.
- [ ] **IaC** (Terraform) for cloud resources.
- [ ] **Staging + prod environments** with env-scoped config.

**Done when:** a merge to main runs the full pipeline and can deploy to staging
with one approval.

---

## Phase 7 — Product depth (analyst & business value) 🟡 ⏱ ongoing
**Goal:** the thing people actually use day to day.

- [ ] **Case-management workflow**: queue → assign → investigate → resolve, with
      the analyst decision feeding the training labels (close the loop).
- [ ] **Explainability** upgrade: SHAP/Integrated Gradients per decision, shown
      in the UI ("why this score").
- [ ] **Step-up auth actions** (OTP/SMS) wired to Medium-risk band.
- [ ] **Alerting integrations** (email/Slack/webhook) for High-risk.
- [ ] **Configurable business rules** editable by an admin (thresholds, costs).
- [ ] **Multi-tenant** support if serving multiple partners.

**Done when:** an analyst can work a real queue and their decisions improve the
next model.

---

## Suggested order for a corporate MVP demo
If the goal is a convincing MVP (not the full platform): **Phase 0 → 1 → 2 →
4 (auth + validation) → 5 (audit + basic dashboards) → 6 (Docker + CI)**, with a
slice of Phase 7 (explainability + case queue). That demonstrates real data,
real persistence, secure serving, auditability, and reproducible deployment —
the five things that separate "student project" from "MVP."

## Cross-cutting engineering debt to pay down early
- Add a **test suite** (`tests/`) — currently minimal. Start with the sequence
  builder, feature engineering, and `predict` fallback logic.
- Add **type hints + mypy** and **ruff/black** in CI.
- Centralize config via **env vars + pydantic-settings** (12-factor).
- Replace `print`/`log()` with **structured logging**.
