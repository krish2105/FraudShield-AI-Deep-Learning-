"""
tracking.py
===========
Experiment tracking + model registry (Phase 3) — MLflow.

Each training run logs its parameters, per-model metrics, and the primary
model + preprocessing artifacts to a local MLflow store (`mlruns/`) and
registers a new version of the `fraudshield_primary` model. Browse it with:

    mlflow ui            # then open http://localhost:5000

If MLflow is not installed, every function here is a safe no-op so training is
never blocked (the dependency lives in requirements-dev.txt).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

try:
    import mlflow
    _HAVE_MLFLOW = True
except Exception:  # pragma: no cover
    _HAVE_MLFLOW = False

try:
    from . import config
    from .utils import log
except ImportError:  # pragma: no cover
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src.utils import log

EXPERIMENT = "fraudshield"
REGISTERED_MODEL = "fraudshield_primary"
# Local SQLite tracking store inside the repo (no server required). MLflow 3
# deprecated the bare file store, so we use a sqlite backend + a local artifact
# directory — both are gitignored.
_TRACKING_URI = f"sqlite:///{config.PROJECT_ROOT / 'mlflow.db'}"
_ARTIFACT_URI = (config.PROJECT_ROOT / "mlartifacts").as_uri()


def _primary_path(primary: str) -> Path:
    return {
        "lstm": config.LSTM_MODEL_PATH, "gru": config.GRU_MODEL_PATH,
        "cnn": config.CNN_MODEL_PATH, "dense_nn": config.DENSE_MODEL_PATH,
    }.get(primary, config.LSTM_MODEL_PATH)


def log_training_run(params: Dict, metrics: Dict, primary: str) -> None:
    """Log a full training run to MLflow + register the primary model version.
    Best-effort: any failure is swallowed so training always completes."""
    if not _HAVE_MLFLOW:
        log("MLflow not installed — skipping experiment tracking "
            "(pip install -r requirements-dev.txt to enable).")
        return
    try:
        mlflow.set_tracking_uri(_TRACKING_URI)
        try:
            mlflow.set_experiment(EXPERIMENT)
        except Exception:
            mlflow.create_experiment(EXPERIMENT, artifact_location=_ARTIFACT_URI)
            mlflow.set_experiment(EXPERIMENT)
        with mlflow.start_run() as run:
            mlflow.log_params({str(k): v for k, v in params.items()})
            for model_name, m in metrics.items():
                if not isinstance(m, dict):
                    continue
                for metric in ("pr_auc", "roc_auc", "recall", "precision", "f1",
                               "recall_at_p90", "accuracy"):
                    val = m.get(metric)
                    if isinstance(val, (int, float)):
                        mlflow.log_metric(f"{model_name}_{metric}", float(val))
            mlflow.set_tag("primary_model", primary)

            # Log the artifacts a deployment needs (model + preprocessing).
            for art in (_primary_path(primary), config.SCALER_PATH,
                        config.ARTIFACTS_PATH, config.METRICS_PATH):
                if Path(art).exists():
                    mlflow.log_artifact(str(art), artifact_path="model")

            # Register a new version of the primary model in the registry,
            # pointing at the artifacts we just logged for this run.
            try:
                from mlflow.tracking import MlflowClient
                client = MlflowClient()
                try:
                    client.create_registered_model(REGISTERED_MODEL)
                except Exception:
                    pass  # already exists
                client.create_model_version(
                    name=REGISTERED_MODEL,
                    source=f"{run.info.artifact_uri}/model",
                    run_id=run.info.run_id,
                    tags={"primary_model": primary},
                )
            except Exception as exc:  # registry optional
                log(f"MLflow run logged; registry version step skipped ({exc}).")
        log(f"Logged training run to MLflow ({_TRACKING_URI}). "
            f"View with: mlflow ui")
    except Exception as exc:  # never let tracking break training
        log(f"MLflow tracking skipped ({exc}).")
