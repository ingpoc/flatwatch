from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

from .database import get_db_connection

try:
    from claude_agent_sdk import ClaudeAgentOptions, query
except Exception:  # pragma: no cover - exercised only when SDK missing
    ClaudeAgentOptions = None
    query = None


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _build_context_snapshot() -> dict[str, Any]:
    conn = get_db_connection()
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
    conn.close()

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


def _fallback_response(prompt: str, context: dict[str, Any], session: dict[str, Any]) -> str:
    query_lower = prompt.lower()
    summary = context["summary"]

    if "balance" in query_lower:
        return (
            f"Current balance is ₹{summary['balance']:.0f}. "
            f"Inflow is ₹{summary['inflow']:.0f}, outflow is ₹{summary['outflow']:.0f}."
        )
    if "unverified" in query_lower:
        return f"There are {summary['unverified_count']} unverified transactions right now."
    if "water" in query_lower:
        recent = [
            transaction
            for transaction in context["recent_transactions"]
            if "water" in (transaction.get("description") or "").lower()
        ]
        if recent:
            match = recent[0]
            return (
                f"Latest water-related transaction: ₹{match['amount']:.0f} on "
                f"{match['timestamp']} ({match['transaction_type']})."
            )

    capability_label = ", ".join(session["allowed_capabilities"]) or "financial summaries"
    return (
        f"FlatWatch agent is running in {session['mode']} mode. "
        f"I can help with {capability_label}. "
        f"Current balance is ₹{summary['balance']:.0f}."
    )


def _extract_text(message: Any) -> Optional[str]:
    result = getattr(message, "result", None)
    if isinstance(result, str):
        return result

    content = getattr(message, "content", None)
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        joined = "".join(parts).strip()
        return joined or None

    return None


def _extract_stream_text(message: Any) -> Optional[str]:
    event = getattr(message, "event", None)
    if not isinstance(event, dict):
        return None
    if event.get("type") != "content_block_delta":
        return None
    delta = event.get("delta", {})
    if isinstance(delta, dict) and delta.get("type") == "text_delta":
        text = delta.get("text")
        return text if isinstance(text, str) else None
    return None


def _sdk_is_configured() -> bool:
    return query is not None and ClaudeAgentOptions is not None and bool(os.getenv("ANTHROPIC_API_KEY"))


async def stream_agent_response(session: dict[str, Any], prompt: str) -> AsyncGenerator[dict[str, Any], None]:
    yield {
        "type": "init",
        "session_id": session["session_id"],
        "sdk_session_id": session.get("sdk_session_id"),
        "mode": session["mode"],
    }

    if session["mode"] == "blocked":
        yield {
            "type": "error",
            "error": "Subscription required before starting an agent session.",
            "timestamp": _now_ms(),
        }
        return

    context_snapshot = _build_context_snapshot()
    if not _sdk_is_configured():
        content = _fallback_response(prompt, context_snapshot, session)
        yield {"type": "assistant_delta", "content": content, "timestamp": _now_ms()}
        yield {
            "type": "result",
            "content": content,
            "sdk_session_id": session.get("sdk_session_id"),
            "timestamp": _now_ms(),
        }
        return

    try:
        final_text = ""
        sdk_session_id = session.get("sdk_session_id")
        options = ClaudeAgentOptions(
            resume=sdk_session_id or None,
            allowed_tools=[],
            permission_mode="acceptEdits",
            include_partial_messages=True,
        )
        compiled_prompt = (
            "You are the FlatWatch portfolio agent. "
            f"Mode: {session['mode']}. "
            f"Allowed capabilities: {', '.join(session['allowed_capabilities']) or 'none'}. "
            f"Context snapshot: {context_snapshot}\n\n"
            f"User request: {prompt}"
        )

        async for message in query(prompt=compiled_prompt, options=options):
            message_session_id = getattr(message, "session_id", None)
            if isinstance(message_session_id, str):
                sdk_session_id = message_session_id

            partial = _extract_stream_text(message)
            if partial:
                yield {
                    "type": "assistant_delta",
                    "content": partial,
                    "timestamp": _now_ms(),
                }

            text = _extract_text(message)
            if text:
                final_text = text

        final = final_text or _fallback_response(prompt, context_snapshot, session)
        yield {
            "type": "result",
            "content": final,
            "sdk_session_id": sdk_session_id,
            "timestamp": _now_ms(),
        }
    except Exception as error:  # pragma: no cover - depends on SDK runtime
        content = _fallback_response(prompt, context_snapshot, session)
        yield {
            "type": "tool_result",
            "tool": "fallback_runtime",
            "status": error.__class__.__name__,
            "content": str(error),
            "timestamp": _now_ms(),
        }
        yield {"type": "assistant_delta", "content": content, "timestamp": _now_ms()}
        yield {
            "type": "result",
            "content": content,
            "sdk_session_id": session.get("sdk_session_id"),
            "timestamp": _now_ms(),
        }
