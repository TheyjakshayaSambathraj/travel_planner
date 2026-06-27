from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from models.travel_package import TravelPackage
from models.travel_request import TravelRequest


class TripHistoryDB:
    def __init__(self, db_path: Optional[str] = None) -> None:
        base_path = Path(db_path) if db_path else Path(__file__).resolve().parents[1] / "tripmind_trips.sqlite3"
        self.db_path = base_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trips (
                    trip_id TEXT PRIMARY KEY,
                    destination TEXT NOT NULL,
                    budget INTEGER NOT NULL,
                    duration INTEGER NOT NULL,
                    persona TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    package_json TEXT NOT NULL,
                    request_json TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def save_trip(self, request: TravelRequest, trip_package: TravelPackage) -> str:
        trip_id = uuid4().hex
        created_at = datetime.utcnow().isoformat() + "Z"
        payload = {
            "trip_id": trip_id,
            "destination": request.destination,
            "budget": request.budget,
            "duration": request.days,
            "persona": request.persona,
            "created_at": created_at,
            "summary_json": self._dump(trip_package.summary),
            "package_json": self._dump(trip_package),
            "request_json": self._dump(request),
        }

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO trips (
                    trip_id, destination, budget, duration, persona, created_at,
                    summary_json, package_json, request_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["trip_id"],
                    payload["destination"],
                    payload["budget"],
                    payload["duration"],
                    payload["persona"],
                    payload["created_at"],
                    payload["summary_json"],
                    payload["package_json"],
                    payload["request_json"],
                ),
            )
            connection.commit()
        return trip_id

    def list_recent_trips(self, limit: int = 8) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT trip_id, destination, budget, duration, persona, created_at, summary_json, package_json, request_json
                FROM trips
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def load_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT trip_id, destination, budget, duration, persona, created_at, summary_json, package_json, request_json
                FROM trips
                WHERE trip_id = ?
                """,
                (trip_id,),
            ).fetchone()
        return dict(row) if row else None

    def delete_trip(self, trip_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM trips WHERE trip_id = ?", (trip_id,))
            connection.commit()

    def duplicate_trip(self, trip_id: str) -> Optional[str]:
        record = self.load_trip(trip_id)
        if not record:
            return None
        request = TravelRequest.parse_obj(json.loads(record["request_json"]))
        package = TravelPackage.parse_obj(json.loads(record["package_json"]))
        return self.save_trip(request, package)

    def search_trips(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        normalized = f"%{query.strip().lower()}%"
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT trip_id, destination, budget, duration, persona, created_at, summary_json, package_json, request_json
                FROM trips
                WHERE LOWER(destination) LIKE ? OR LOWER(persona) LIKE ?
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (normalized, normalized, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _dump(value: Any) -> str:
        if hasattr(value, "model_dump"):
            data = value.model_dump()
            return json.dumps(data, ensure_ascii=False, default=str)
        if hasattr(value, "dict"):
            data = value.dict()
            return json.dumps(data, ensure_ascii=False, default=str)
        return json.dumps(value, ensure_ascii=False, default=str)
