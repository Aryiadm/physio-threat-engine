"""
FastAPI application for the Physiological Threat Intelligence Engine.

This app exposes a RESTful interface allowing clients to ingest health data,
compute trust scores, detect anomalies, analyse cross‑signal correlations and
simulate adversarial conditions. It demonstrates how to treat personal health
data like untrusted telemetry and apply zero‑trust analytics inspired by
network security systems.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

# Import sibling modules directly.  When running this file via uvicorn
# from within the backend directory, Python adds the current directory to
# sys.path so these imports will resolve correctly.
import db  # noqa: E402
import schemas  # noqa: E402
import model  # noqa: E402

app = FastAPI(title="Physiological Threat Intelligence Engine", version="0.1.0")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    """Initialise the database when the server starts."""
    db.init_db()


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/records", response_model=schemas.HealthRecordOut)
def create_or_update_record(rec: schemas.HealthRecordIn) -> schemas.HealthRecordOut:
    """Insert or update a health record for a user."""
    rec_id = db.upsert_record(rec.model_dump())
    return schemas.HealthRecordOut(id=rec_id, **rec.model_dump())


@app.get("/records/{user_id}", response_model=list[schemas.HealthRecordOut])
def list_records(user_id: str) -> list[schemas.HealthRecordOut]:
    """Return all health records for a user sorted by date."""
    rows = db.fetch_user_records(user_id)
    return [schemas.HealthRecordOut(**r) for r in rows]


@app.get("/trust/{user_id}", response_model=schemas.TrustScoresOut)
def get_trust_scores(user_id: str) -> schemas.TrustScoresOut:
    """Compute trust scores for all records of a user."""
    rows = db.fetch_user_records(user_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No data found for user")
    df = pd.DataFrame(rows)
    df_sorted = df.sort_values("date")
    _, trust_entries = model.compute_trust_scores(df_sorted)
    return schemas.TrustScoresOut(user_id=user_id, scores=[schemas.TrustScore(**t) for t in trust_entries])


@app.get("/anomaly/{user_id}", response_model=schemas.AnomalyListOut)
def get_anomalies(user_id: str) -> schemas.AnomalyListOut:
    """Compute anomaly scores for all days of a user."""
    rows = db.fetch_user_records(user_id)
    if len(rows) < 5:
        raise HTTPException(status_code=400, detail="Insufficient data for anomaly detection (need at least 5 records)")
    df = pd.DataFrame(rows).sort_values("date")
    results = model.compute_anomalies(df)
    return schemas.AnomalyListOut(user_id=user_id, results=[schemas.AnomalyOut(**r) for r in results])


@app.get("/correlations/{user_id}", response_model=schemas.CorrelationMatrixOut)
def get_correlations(user_id: str) -> schemas.CorrelationMatrixOut:
    """Compute pairwise correlations between metrics for a user."""
    rows = db.fetch_user_records(user_id)
    if len(rows) < 3:
        raise HTTPException(status_code=400, detail="Insufficient data to compute correlations (need at least 3 records)")
    df = pd.DataFrame(rows).sort_values("date")
    corrs = model.compute_correlations(df)
    return schemas.CorrelationMatrixOut(user_id=user_id, correlations=[schemas.CorrelationEntry(**c) for c in corrs])


@app.post("/simulate", response_model=schemas.SimulationResult)
def simulate(request: schemas.SimulationRequest) -> schemas.SimulationResult:
    """Simulate adversarial tampering on a user's data and return detection results."""
    rows = db.fetch_user_records(request.user_id)
    if len(rows) < 5:
        raise HTTPException(status_code=400, detail="Insufficient data to perform simulation")
    df = pd.DataFrame(rows).sort_values("date")
    # Apply perturbation
    tampered = model.simulate_attack(df, mode=request.mode, fraction=request.fraction)
    # Detect anomalies on tampered data
    results = model.compute_anomalies(tampered)
    # Convert tampered df back to list of dicts
    tampered_records: List[dict] = tampered.to_dict(orient="records")
    return schemas.SimulationResult(
        user_id=request.user_id,
        mode=request.mode,
        modified_records=[schemas.HealthRecordOut(**r) for r in tampered_records],
        detected_anomalies=[schemas.AnomalyOut(**r) for r in results],
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return a JSON error."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})
