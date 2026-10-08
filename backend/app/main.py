import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import models  # noqa: F401  (register tables)
from .config import CORS_ORIGINS, SEED_DEMO_DATA
from .database import Base, SessionLocal, engine
from .ml_service import register_model_versions
from .routers import (appointments, audit_logs, auth, dashboard, departments, doctors, patients, predictions,
                      records, users)
from .seed import seed

log = logging.getLogger("smart_hospital")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if SEED_DEMO_DATA:
            seed(db)
        register_model_versions(db)
    yield


app = FastAPI(title="Smart Hospital Management & Disease Risk Prediction", version="0.7.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth, users, departments, doctors, patients, appointments, records, predictions, dashboard, audit_logs):
    app.include_router(r.router)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    # Report field + message only; never echo submitted values back (they may be patient data).
    errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse({"detail": "Validation failed", "errors": errors}, status_code=422)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error", exc_info=exc)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}
