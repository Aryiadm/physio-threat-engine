"""
SQLite helper functions for the Physiological Threat Intelligence Engine.

This module encapsulates basic operations against the database used to store
health records. It uses Python's built‑in sqlite3 module and sets a row
factory so that rows behave like dictionaries.
"""

import sqlite3
from typing import Any, Dict, List, Optional


DB_PATH = "health_threat_engine.sqlite3"


def connect() -> sqlite3.Connection:
    """Create a new SQLite connection with row dictionary access."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialise the database schema if it does not already exist."""
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS health_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            sleep_hours REAL,
            resting_hr REAL,
            hrv REAL,
            steps INTEGER,
            calories REAL,
            weight REAL,
            UNIQUE(user_id, date)
        );
        """
    )
    conn.commit()
    conn.close()


def upsert_record(rec: Dict[str, Any]) -> int:
    """Insert or update a health record and return its primary key.

    If a record for the same user_id and date already exists, it will be
    updated with the new values. Missing fields in the input will set the
    corresponding column to NULL.
    """
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO health_records (user_id, date, sleep_hours, resting_hr, hrv, steps, calories, weight)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, date) DO UPDATE SET
            sleep_hours=excluded.sleep_hours,
            resting_hr=excluded.resting_hr,
            hrv=excluded.hrv,
            steps=excluded.steps,
            calories=excluded.calories,
            weight=excluded.weight;
        """,
        (
            rec["user_id"],
            rec["date"],
            rec.get("sleep_hours"),
            rec.get("resting_hr"),
            rec.get("hrv"),
            rec.get("steps"),
            rec.get("calories"),
            rec.get("weight"),
        ),
    )
    conn.commit()
    # Retrieve the id for the inserted/updated record
    cur.execute(
        "SELECT id FROM health_records WHERE user_id=? AND date=?",
        (rec["user_id"], rec["date"]),
    )
    row = cur.fetchone()
    conn.close()
    return int(row["id"])


def fetch_user_records(user_id: str) -> List[Dict[str, Any]]:
    """Return all health records for a user ordered by date."""
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM health_records
        WHERE user_id=?
        ORDER BY date ASC;
        """,
        (user_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def fetch_record(user_id: str, date: str) -> Optional[Dict[str, Any]]:
    """Return a single health record for a user on a given date."""
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM health_records
        WHERE user_id=? AND date=?
        LIMIT 1;
        """,
        (user_id, date),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None
