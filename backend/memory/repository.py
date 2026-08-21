"""Durable interaction history in PostgreSQL with in-memory fallback."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from backend.engine.fallback import fallback_manager

logger = logging.getLogger("intent_memory")

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS interaction_history (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    transcript TEXT,
    action TEXT,
    targets JSONB,
    decision TEXT,
    language TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS interaction_history_session_idx
    ON interaction_history (session_id, created_at DESC);
"""


class ContextRepository:
    def __init__(self, conn: Any | None = None) -> None:
        self._mem: dict[str, list[dict[str, Any]]] = {}
        self._conn = conn
        if self._conn is None:
            self._conn = self._connect()
        if self._conn is not None:
            try:
                self._ensure_schema()
            except Exception as exc:
                logger.warning("Postgres schema init failed: %s", exc)
                fallback_manager.postgres_failed()
                self._conn = None

    def _connect(self) -> Any | None:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            return None
        try:
            import psycopg  # type: ignore

            conn = psycopg.connect(dsn, connect_timeout=1, autocommit=True)
            return conn
        except Exception as exc:
            logger.warning("PostgreSQL unavailable, using in-memory history: %s", exc)
            fallback_manager.postgres_failed()
            return None

    def _ensure_schema(self) -> None:
        if self._conn is None:
            return
        with self._conn.cursor() as cur:
            cur.execute(_CREATE_SQL)

    @property
    def postgres_ok(self) -> bool:
        return self._conn is not None

    def append_turn(
        self,
        session_id: str,
        *,
        transcript: str | None,
        action: str | None,
        targets: list[str],
        decision: str,
        language: str | None = None,
    ) -> None:
        row = {
            "transcript": transcript,
            "action": action,
            "targets": list(targets),
            "decision": decision,
            "language": language,
        }
        self._mem.setdefault(session_id, []).append(row)
        if self._conn is None:
            return
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO interaction_history
                        (session_id, transcript, action, targets, decision, language)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                    """,
                    (session_id, transcript, action, json.dumps(targets), decision, language),
                )
        except Exception as exc:
            logger.warning("Postgres insert failed: %s", exc)
            fallback_manager.postgres_failed()
            self._conn = None

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        rows: list[dict[str, Any]] = []
        if self._conn is not None:
            try:
                with self._conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT transcript, action, targets, decision, language
                        FROM interaction_history
                        WHERE session_id = %s
                        ORDER BY created_at DESC
                        LIMIT 20
                        """,
                        (session_id,),
                    )
                    fetched = cur.fetchall()
                    for transcript, action, targets, decision, language in fetched:
                        if isinstance(targets, str):
                            targets = json.loads(targets)
                        rows.append({
                            "transcript": transcript,
                            "action": action,
                            "targets": targets or [],
                            "decision": decision,
                            "language": language,
                        })
                rows.reverse()
            except Exception as exc:
                logger.warning("Postgres load failed: %s", exc)
                fallback_manager.postgres_failed()
                self._conn = None
                rows = list(self._mem.get(session_id, []))
        else:
            rows = list(self._mem.get(session_id, []))

        if not rows:
            return None
        last = next((r for r in reversed(rows) if r.get("targets")), rows[-1])
        targets = last.get("targets") or []
        return {
            "current_target": targets[-1] if targets else None,
            "recent_targets": targets,
            "recent_interactions": rows[-8:],
        }


_repo: ContextRepository | None = None


def get_repository() -> ContextRepository:
    global _repo
    if _repo is None:
        _repo = ContextRepository()
    return _repo


def reset_repository_for_tests(repo: ContextRepository | None = None) -> ContextRepository:
    global _repo
    _repo = repo if repo is not None else ContextRepository(conn=None)
    return _repo
