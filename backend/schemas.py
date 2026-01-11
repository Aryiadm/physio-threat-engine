"""
Pydantic schemas for the Physiological Threat Intelligence Engine backend.

"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class HealthRecordIn(BaseModel):
    """Schema for incoming health record data.

    Each record represents a single day of aggregated health information from
    disparate sources (wearables, nutrition logs, smart scales, etc.). Fields
    are optional because real‑world streams often contain missing data. When
    values are omitted the ingestion pipeline treats them as missing signals.
    """

    user_id: str = Field(..., description="Unique identifier for the user")
    date: str = Field(..., description="Date in ISO format YYYY‑MM‑DD")
    sleep_hours: Optional[float] = Field(None, description="Total hours slept")
    resting_hr: Optional[float] = Field(None, description="Resting heart rate (bpm)")
    hrv: Optional[float] = Field(None, description="Heart rate variability (ms)")
    steps: Optional[int] = Field(None, description="Number of steps taken")
    calories: Optional[float] = Field(None, description="Calories consumed")
    weight: Optional[float] = Field(None, description="Body weight (kg)")


class HealthRecordOut(HealthRecordIn):
    """Schema returned when a record is created or retrieved.

    Inherits all fields from HealthRecordIn and adds a database primary key.
    """

    id: int = Field(..., description="Database primary key")


class TrustScore(BaseModel):
    """Trust score for a single metric on a given day.

    The score lies in [0,1], where 1 represents complete confidence in the
    veracity of the signal and 0 denotes an entirely untrusted value. A score
    of 0.5 implies partial confidence. The drivers field provides context on
    why the score was assigned (missingness, distribution shift, etc.).
    """

    metric: str
    date: str
    score: float
    drivers: List[str]


class TrustScoresOut(BaseModel):
    """Aggregated trust scores for a user.

    Contains a list of TrustScore entries, one per metric per day.
    """

    user_id: str
    scores: List[TrustScore]


class AnomalyDriver(BaseModel):
    """Represents a metric contributing to an anomaly detection score."""

    metric: str
    value: Optional[float]
    z_score: float
    direction: str


class AnomalyOut(BaseModel):
    """Anomaly result for a specific day.

    The anomaly_score is a continuous value summarising the deviation of the
    day's metrics from the baseline. If it exceeds a tuned threshold the day
    is considered anomalous. Drivers explain which metrics contributed most.
    """

    user_id: str
    date: str
    anomaly_score: float
    is_anomaly: bool
    drivers: List[AnomalyDriver]
    narrative: str


class AnomalyListOut(BaseModel):
    """List of anomaly results for multiple days."""

    user_id: str
    results: List[AnomalyOut]


class CorrelationEntry(BaseModel):
    """Entry in the correlation matrix between two metrics."""

    metric_x: str
    metric_y: str
    correlation: float


class CorrelationMatrixOut(BaseModel):
    """Correlation matrix across metrics for a user.

    The matrix is flattened into a list of correlation entries. The frontend can
    reconstruct a table or graph from these entries.
    """

    user_id: str
    correlations: List[CorrelationEntry]


class SimulationRequest(BaseModel):
    """Request body for simulating data tampering or noise injection."""

    user_id: str
    mode: str = Field(
        ...,
        description="Type of simulation: missing, delay, spoof, noise",
        pattern="^(missing|delay|spoof|noise)$",
    )
    fraction: float = Field(
        0.1,
        ge=0.0,
        le=1.0,
        description="Fraction of records/values to affect (default 0.1)",
    )


class SimulationResult(BaseModel):
    """Response to a simulation request.

    Contains the tampered records and detection results to illustrate how the
    system responds to adversarial conditions.
    """

    user_id: str
    mode: str
    modified_records: List[HealthRecordOut]
    detected_anomalies: List[AnomalyOut]
