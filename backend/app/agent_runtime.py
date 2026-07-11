from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

from .database import get_db
from .runtime_config import resolve_runtime_policy

logger = logging.getLogger(__name__)

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_SHARED_ROOT = _WORKSPACE_ROOT / "shared"
if str(_SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_ROOT))

from cursor_agent_runtime.streaming import stream_cursor_response  # noqa: E402


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _build_context_snapshot() -> dict[str, Any]:
    with get_db() as conn:
        summary_row = conn.execute(
            """
            SELECT
              COALESCE(SUM(CASE WHEN transaction_type = 'inflow' THEN amount ELSE 0 END), 0) AS inflow,
              COALESCE(SUM(CASE WHEN transaction_type = 'outflow' THEN amount ELSE 0 END), 0) AS outflow,
              COALESCE(SUM(CASE WHEN transaction_type = 'inflow' THEN amount ELSE -amount END), 0) AS balance,
              COALESCE(SUM(CASE WHEN verified = 0 THEN 1 ELSE 0 END), 0) AS unverified_count
            FROM transactions
            """
        ).fetchone()
        recent_transactions = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, amount, transaction_type, description, vpa, timestamp, verified
                FROM transactions
                ORDER BY timestamp DESC
                LIMIT 5
                """
            ).fetchall()
        ]
        recent_challenges = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, transaction_id, reason, status, created_at
                FROM challenges
                ORDER BY created_at DESC
                LIMIT 5
                """
            ).fetchall()
        ]

    return {
        "summary": {
            "balance": summary_row["balance"],
            "inflow": summary_row["inflow"],
            "outflow": summary_row["outflow"],
            "unverified_count": summary_row["unverified_count"],
        },
        "recent_transactions": recent_transactions,
        "recent_challenges": recent_challenges,
    }


def _system_prefix(session: dict[str, Any], runtime_snapshot: dict[str, Any]) -> str:
    context_snapshot = _build_context_snapshot()
    return (
        "You are a portfolio agent backed by the Cursor SDK.\n"
        f"App: {session.get('app_id', 'flatwatch')}\n"
        f"Mode: {session['mode']}\n"
        f"Allowed capabilities: {', '.join(session['allowed_capabilities']) or 'none'}\n"
        f"Trust state: {session['trust_state']}\n"
        f"Task type: {session['task_type']}\n"
        f"Context: {session['context']}\n"
        f"Runtime model: {runtime_snapshot['model']}\n"
        f"Operational snapshot: {context_snapshot}"
    )


async def stream_agent_response(
    session: dict[str, Any],
    prompt: str,
    runtime_snapshot: dict[str, Any],
) -> AsyncGenerator[dict[str, Any], None]:
    session.setdefault("app_id", "flatwatch")
    async for event in stream_cursor_response(
        prompt=prompt,
        cwd=os.getcwd(),
        runtime_snapshot=runtime_snapshot,
        session=session,
        system_prefix=_system_prefix(session, runtime_snapshot),
        resume_agent_id=session.get("sdk_session_id"),
    ):
        yield event
