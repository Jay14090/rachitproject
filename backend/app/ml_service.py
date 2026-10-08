"""Inference wrapper for the trained risk models (training lives in /ml)."""
import json
import logging
from datetime import datetime
from functools import lru_cache

import joblib
import pandas as pd
import sklearn

from .config import ML_ARTIFACT_DIR

log = logging.getLogger(__name__)

RISK_LEVELS = [(0.33, "low"), (0.66, "moderate"), (1.01, "high")]

# API/disease_type name -> artifact file prefix produced by ml/train_*.py
DISEASES = {"diabetes": "diabetes", "heart_disease": "heart"}


class RiskModel:
    def __init__(self, disease: str) -> None:
        prefix = DISEASES[disease]
        self.disease = disease
        self.meta = json.loads((ML_ARTIFACT_DIR / f"{prefix}_meta.json").read_text())
        trained_with = self.meta.get("sklearn_version")
        if trained_with and trained_with != sklearn.__version__:
            log.warning("%s model was trained with scikit-learn %s but %s is installed; if loading or predictions "
                        "fail, retrain with `python ml/train_%s.py`.", disease, trained_with, sklearn.__version__, prefix)
        self.pipeline = joblib.load(ML_ARTIFACT_DIR / f"{prefix}_model.joblib")
        self.features: list[str] = self.meta["features"]
        self.medians: dict[str, float] = self.meta["feature_medians"]

    @property
    def version(self) -> str:
        return self.meta["version"]

    def _proba(self, rows: pd.DataFrame):
        return self.pipeline.predict_proba(rows[self.features])[:, 1]

    def predict(self, values: dict) -> dict:
        row = pd.DataFrame([{f: values[f] for f in self.features}])
        score = float(self._proba(row)[0])
        level = next(name for limit, name in RISK_LEVELS if score < limit)
        return {
            "risk_score": round(score, 4),
            "risk_level": level,
            "result": "higher risk" if score >= 0.5 else "lower risk",
            "explanation": self.explain(row, score),
        }

    def explain(self, row: pd.DataFrame, base_score: float) -> list[dict]:
        """Model-agnostic local explanation: swap each feature for the training median and
        measure how much the predicted risk moves. Positive impact = this value raises risk."""
        variants = []
        for f in self.features:
            v = row.copy()
            v[f] = self.medians[f]
            variants.append(v)
        scores = self._proba(pd.concat(variants, ignore_index=True))
        out = [{"feature": f, "value": float(row[f].iloc[0]), "impact": round(base_score - float(s), 4)}
               for f, s in zip(self.features, scores)]
        return sorted(out, key=lambda d: abs(d["impact"]), reverse=True)


@lru_cache(maxsize=None)
def get_model(disease: str) -> RiskModel:
    return RiskModel(disease)


def register_model_versions(db) -> None:
    """Make sure every loadable model is recorded in model_versions (idempotent)."""
    from .models import ModelVersion
    for disease in DISEASES:
        try:
            model = get_model(disease)
        except FileNotFoundError:
            log.warning("ML artifacts for %s missing — run the matching ml/train_*.py. "
                        "Its prediction endpoint is disabled.", disease)
            continue
        m = model.meta
        if db.query(ModelVersion).filter_by(version=m["version"]).first():
            continue
        db.query(ModelVersion).filter_by(disease_type=disease).update({"active_flag": False})
        db.add(ModelVersion(disease_type=disease, algorithm=m["algorithm"], version=m["version"],
                            metrics={**m["metrics"], "cv_roc_auc_mean": m["cv_roc_auc_mean"],
                                     "comparison": m["comparison"]},
                            trained_at=datetime.fromisoformat(m["trained_at"]).replace(tzinfo=None),
                            active_flag=True))
        db.commit()
