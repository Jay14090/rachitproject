"""Train and compare diabetes-risk classifiers on the public Pima Indians dataset.

Usage:  python ml/train_diabetes.py
Outputs (ml/artifacts/): diabetes_model.joblib, diabetes_meta.json
"""
from pathlib import Path

import numpy as np
import pandas as pd

from common import train_and_save

RAW = Path(__file__).resolve().parent / "data" / "pima_raw.csv"
COLUMNS = ["pregnancies", "glucose", "blood_pressure", "skin_thickness",
           "insulin", "bmi", "diabetes_pedigree", "age", "outcome"]
FEATURES = COLUMNS[:-1]
# In this dataset a physiologically impossible 0 encodes "missing".
ZERO_IS_MISSING = ["glucose", "blood_pressure", "skin_thickness", "insulin", "bmi"]


def load() -> pd.DataFrame:
    df = pd.read_csv(RAW, header=None, names=COLUMNS)
    df[ZERO_IS_MISSING] = df[ZERO_IS_MISSING].replace(0, np.nan)
    return df


if __name__ == "__main__":
    train_and_save("diabetes", load(), FEATURES, "outcome", "Pima Indians Diabetes (public, de-identified), n=768")
