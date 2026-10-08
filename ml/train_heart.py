"""Train and compare heart-disease-risk classifiers on the public Cleveland (UCI) dataset.

Usage:  python ml/train_heart.py
Outputs (ml/artifacts/): heart_model.joblib, heart_meta.json

Data note: the CSV mirror used here (303 rows) stores target=1 for *healthy* patients (verified: the
target=1 group is younger, has higher max heart rate and lower ST depression). We therefore define
disease = 1 - target. Known invalid codes (thal=0, ca=4) are treated as missing.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from common import train_and_save

RAW = Path(__file__).resolve().parent / "data" / "heart_raw.csv"
FEATURES = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach", "exang", "oldpeak",
            "slope", "ca", "thal"]


def load() -> pd.DataFrame:
    df = pd.read_csv(RAW)
    df.columns = [c.strip().lstrip("﻿") for c in df.columns]
    df["disease"] = 1 - df["target"]
    df["thal"] = df["thal"].replace(0, np.nan)
    df["ca"] = df["ca"].replace(4, np.nan)
    return df


if __name__ == "__main__":
    train_and_save("heart", load(), FEATURES, "disease",
                   "Cleveland Heart Disease (UCI, public, de-identified), n=303")
