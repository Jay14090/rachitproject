"""Shared training / evaluation helpers for the disease-risk models (doc section 9)."""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

try:  # optional advanced model (doc 9.2)
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover
    XGBClassifier = None

OUT = Path(__file__).resolve().parent / "artifacts"
SEED = 42


def make_models() -> dict:
    def pipe(clf, scale):
        steps = [("impute", SimpleImputer(strategy="median"))]
        if scale:
            steps.append(("scale", StandardScaler()))
        steps.append(("clf", clf))
        return Pipeline(steps)

    models = {
        "Logistic Regression": pipe(LogisticRegression(max_iter=2000, class_weight="balanced"), True),
        "Decision Tree": pipe(DecisionTreeClassifier(max_depth=4, min_samples_leaf=10,
                                                     class_weight="balanced", random_state=SEED), False),
        "Random Forest": pipe(RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=5,
                                                     class_weight="balanced", random_state=SEED), False),
    }
    if XGBClassifier is not None:
        models["XGBoost"] = pipe(XGBClassifier(n_estimators=150, max_depth=3, learning_rate=0.05, subsample=0.8,
                                               colsample_bytree=0.8, eval_metric="logloss",
                                               random_state=SEED, n_jobs=1), False)
    return models


def evaluate(model, X, y) -> dict:
    pred = model.predict(X)
    proba = model.predict_proba(X)[:, 1]
    tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
    return {
        "accuracy": round(accuracy_score(y, pred), 4),
        "precision": round(precision_score(y, pred), 4),
        "recall": round(recall_score(y, pred), 4),
        "f1": round(f1_score(y, pred), 4),
        "roc_auc": round(roc_auc_score(y, proba), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def train_and_save(disease: str, df: pd.DataFrame, features: list[str], target: str, dataset_note: str) -> dict:
    """Compare all candidates with 5-fold CV, pick the best by CV ROC-AUC (never by the test set),
    report hold-out test metrics, and write a versioned artifact + metadata."""
    X, y = df[features], df[target]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

    results = {}
    for name, model in make_models().items():
        cv_auc = cross_val_score(model, X_train, y_train, cv=cv, scoring="roc_auc")
        model.fit(X_train, y_train)
        results[name] = {"cv_roc_auc_mean": round(float(cv_auc.mean()), 4),
                         "cv_roc_auc_std": round(float(cv_auc.std()), 4),
                         "test": evaluate(model, X_test, y_test), "_model": model}
        t = results[name]["test"]
        print(f"[{disease}] {name:20s} CV AUC {cv_auc.mean():.3f}±{cv_auc.std():.3f} | "
              f"test acc {t['accuracy']:.3f} rec {t['recall']:.3f} auc {t['roc_auc']:.3f}")

    best = max(results, key=lambda n: results[n]["cv_roc_auc_mean"])
    print(f"[{disease}] selected: {best}")

    OUT.mkdir(exist_ok=True)
    joblib.dump(results[best]["_model"], OUT / f"{disease}_model.joblib")
    meta = {
        "disease": disease,
        "version": f"{disease}-{best.lower().replace(' ', '-')}-v1",
        "algorithm": best,
        "sklearn_version": sklearn.__version__,  # joblib artifacts are only guaranteed to load on the same version
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": dataset_note,
        "features": features,
        "feature_medians": {f: float(X_train[f].median()) for f in features},
        "metrics": results[best]["test"],
        "cv_roc_auc_mean": results[best]["cv_roc_auc_mean"],
        "comparison": {n: {k: v for k, v in r.items() if k != "_model"} for n, r in results.items()},
    }
    (OUT / f"{disease}_meta.json").write_text(json.dumps(meta, indent=2))
    return meta
