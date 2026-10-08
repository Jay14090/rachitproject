import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

# SQLite by default so the project runs with zero setup.
# For MySQL:  mysql+pymysql://user:password@localhost:3306/smart_hospital
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'smart_hospital.db'}")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me-in-production-0123456789")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "480"))

ML_ARTIFACT_DIR = Path(os.getenv("ML_ARTIFACT_DIR", REPO_ROOT / "ml" / "artifacts"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
SEED_DEMO_DATA = os.getenv("SEED_DEMO_DATA", "1") == "1"
