from __future__ import annotations

import inspect
import logging
import os
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from .database import get_db
from .runtime_config import resolve_runtime_policy

logger = logging.getLogger(__name__)

try:
    from claude_agent_sdk import ClaudeAgentOptions, query
    from claude_agent_sdk._errors import MessageParseError
    from claude_agent_sdk._internal import client as sdk_client
    from claude_agent_sdk._internal import message_parser as sdk_message_parser
    from claude_agent_sdk.types import SystemMessage
except ImportError:  # pragma: no cover - exercised only when SDK missing
    ClaudeAgentOptions = None
    query = None
else:  # pragma: no cover - exercised only when SDK is available
    _original_parse_message = sdk_message_parser.parse_message

    def _parse_message_with_rate_limit_support(data: dict[str, Any]):
        try:
            return _original_parse_message(data)
        except MessageParseError:
            if isinstance(data, dict) and data.get("type") == "rate_limit_event":
                return SystemMessage(subtype="rate_limit_event", data=data)
            raise

    sdk_message_parser.parse_message = _parse_message_with_rate_limit_support
    sdk_client.parse_message = _parse_message_with_rate_limit_support


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


def _extract_text(message: Any) -> str | None:
    result = getattr(message, "result", None)
    if isinstance(result, str) and result.strip():
        return result.strip()

    content = getattr(message, "content", None)
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            item_type = getattr(item, "type", None)
            if item_type == "text" and isinstance(getattr(item, "text", None), str):
                text_parts.append(item.text)
        combined = "".join(text_parts).strip()
        return combined or None
    return None


def _extract_stream_text(message: Any) -> str | None:
    event = getattr(message, "event", None)
    if event is None or getattr(event, "type", None) != "content_block_delta":
        return None

    delta = getattr(event, "delta", None)
    if delta is None or getattr(delta, "type", None) != "text_delta":
        return None

    text = getattr(delta, "text", None)
    return text if isinstance(text, str) and text else None


def _extract_cost_usd(message: Any) -> float:
    total_cost_usd = getattr(message, "total_cost_usd", None)
    return float(total_cost_usd) if isinstance(total_cost_usd, (int, float)) else 0.0


async def stream_agent_response(
    session: dict[str, Any],
    prompt: str,
    runtime_snapshot: dict[str, Any],
) -> AsyncGenerator[dict[str, Any], None]:
    yield {
        "type": "init",
        "session_id": session["session_id"],
        "sdk_session_id": session.get("sdk_session_id"),
        "mode": session["mode"],
    }

    if not runtime_snapshot.get("runtime_available") or session["mode"] == "blocked":
        yield {
            "type": "error",
            "error": runtime_snapshot.get("blocked_reason") or "Claude Agent runtime is unavailable.",
            "timestamp": _now_ms(),
        }
        return

    if query is None or ClaudeAgentOptions is None:
        yield {
            "type": "error",
            "error": "claude_agent_sdk is not installed in the FlatWatch backend environment.",
            "timestamp": _now_ms(),
        }
        return

    try:
        final_text = ""
        total_cost_usd = 0.0
        sdk_session_id = session.get("sdk_session_id")
        runtime_policy = resolve_runtime_policy()
        context_snapshot = _build_context_snapshot()
        options_kwargs: dict[str, Any] = {
            "model": runtime_snapshot["model"],
            "resume": sdk_session_id or None,
            "tools": [],
            "allowed_tools": [],
            "permission_mode": "default",
            "include_partial_messages": True,
            "cwd": os.getcwd(),
        }
        if "cli_path" in inspect.signature(ClaudeAgentOptions).parameters:
            options_kwargs["cli_path"] = runtime_policy.claude_code_executable_path
        options = ClaudeAgentOptions(**options_kwargs)
        compiled_prompt = (
            "You are the FlatWatch portfolio agent.\n"
            f"Mode: {session['mode']}\n"
            f"Allowed capabilities: {', '.join(session['allowed_capabilities']) or 'none'}\n"
            f"Trust state: {session['trust_state']}\n"
            f"Task type: {session['task_type']}\n"
            f"Context: {session['context']}\n"
            f"Runtime model: {runtime_snapshot['model']}\n"
            f"Operational snapshot: {context_snapshot}\n\n"
            f"User request: {prompt}"
        )

        async for message in query(prompt=compiled_prompt, options=options):
            message_session_id = getattr(message, "session_id", None)
            if isinstance(message_session_id, str):
                sdk_session_id = message_session_id

            total_cost_usd = max(total_cost_usd, _extract_cost_usd(message))

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

        if not final_text:
            raise RuntimeError("Claude Agent SDK returned no assistant content.")

        yield {
            "type": "result",
            "content": final_text,
            "sdk_session_id": sdk_session_id,
            "estimated_cost_usd": total_cost_usd or None,
            "timestamp": _now_ms(),
        }
    except Exception:  # pragma: no cover - depends on SDK runtime
        logger.exception("FlatWatch agent runtime failed.")
        yield {
            "type": "error",
            "error": "FlatWatch agent runtime failed to process the request.",
            "timestamp": _now_ms(),
        }
