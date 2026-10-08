"""Train and compare diabetes-risk classifiers on the public Pima Indians dataset.

Workflow (doc section 9.1): load -> clean -> split -> cross-validate ->
evaluate on held-out test set -> select best model -> save versioned artifact.

Usage:  python ml/train_diabetes.py
Outputs (ml/artifacts/):
    diabetes_model.joblib   fitted sklearn Pipeline of the selected model
    diabetes_meta.json      model version, features, metrics, medians for explanations
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "pima_raw.csv"
OUT = ROOT / "artifacts"
SEED = 42

COLUMNS = ["pregnancies", "glucose", "blood_pressure", "skin_thickness",
           "insulin", "bmi", "diabetes_pedigree", "age", "outcome"]
FEATURES = COLUMNS[:-1]
# In this dataset a physiologically impossible 0 encodes "missing".
ZERO_IS_MISSING = ["glucose", "blood_pressure", "skin_thickness", "insulin", "bmi"]


def load() -> pd.DataFrame:
    df = pd.read_csv(RAW, header=None, names=COLUMNS)
    df[ZERO_IS_MISSING] = df[ZERO_IS_MISSING].replace(0, np.nan)
    return df


def make_models() -> dict:
    def pipe(clf, scale):
        steps = [("impute", SimpleImputer(strategy="median"))]
        if scale:
            steps.append(("scale", StandardScaler()))
        steps.append(("clf", clf))
        return Pipeline(steps)

    return {
        "Logistic Regression": pipe(LogisticRegression(max_iter=1000, class_weight="balanced"), True),
        "Decision Tree": pipe(DecisionTreeClassifier(max_depth=4, min_samples_leaf=10,
                                                     class_weight="balanced", random_state=SEED), False),
        "Random Forest": pipe(RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=5,
                                                     class_weight="balanced", random_state=SEED), False),
    }


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


def main() -> None:
    df = load()
    X, y = df[FEATURES], df["outcome"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    results = {}
    for name, model in make_models().items():
        cv_auc = cross_val_score(model, X_train, y_train, cv=cv, scoring="roc_auc")
        model.fit(X_train, y_train)
        results[name] = {
            "cv_roc_auc_mean": round(float(cv_auc.mean()), 4),
            "cv_roc_auc_std": round(float(cv_auc.std()), 4),
            "test": evaluate(model, X_test, y_test),
            "_model": model,
        }
        print(f"{name:20s} CV AUC {cv_auc.mean():.3f}±{cv_auc.std():.3f}  test {results[name]['test']}")

    # Selection is by cross-validated ROC-AUC on the training split (not test), per doc 9.2.
    best = max(results, key=lambda n: results[n]["cv_roc_auc_mean"])
    print(f"Selected: {best}")

    OUT.mkdir(exist_ok=True)
    joblib.dump(results[best]["_model"], OUT / "diabetes_model.joblib")
    version = f"diabetes-{best.lower().replace(' ', '-')}-v1"
    meta = {
        "disease": "diabetes",
        "version": version,
        "algorithm": best,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": "Pima Indians Diabetes (public, de-identified), n=768",
        "features": FEATURES,
        "feature_medians": {f: float(X_train[f].median()) for f in FEATURES},
        "metrics": results[best]["test"],
        "cv_roc_auc_mean": results[best]["cv_roc_auc_mean"],
        "comparison": {n: {k: v for k, v in r.items() if k != "_model"} for n, r in results.items()},
    }
    (OUT / "diabetes_meta.json").write_text(json.dumps(meta, indent=2))
    print("Saved", version)


if __name__ == "__main__":
    main()
