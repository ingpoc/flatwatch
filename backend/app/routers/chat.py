# Chat router for FlatWatch
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from ..rbac import require_resident
from ..auth import User
from ..chat import query_transactions
from ..control_plane import build_runtime_snapshot, get_agent_session, record_usage, save_agent_session
from ..agent_runtime import stream_agent_response
from ..trust import fetch_trust_snapshot


class ChatRequest(BaseModel):
    query: str
    session_id: str = None


class ChatResponse(BaseModel):
    query: str
    response: str
    session_id: str
    timestamp: str


router = APIRouter(prefix="/api/chat", tags=["Chat"])


def _persist_chat_session(
    *,
    session: dict[str, Any],
    user_id: int,
    wallet_address: Optional[str],
) -> None:
    save_agent_session(
        session_id=session["session_id"],
        app_id="flatwatch",
        user_id=user_id,
        subject_id=session["subject_id"],
        wallet_address=wallet_address,
        sdk_session_id=session["sdk_session_id"],
        trust_state=session["trust_state"],
        mode=session["mode"],
        allowed_capabilities=session["allowed_capabilities"],
        task_type=session["task_type"],
        context=session["context"],
        messages=session["messages"],
    )


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    http_request: Request,
    current_user: User = Depends(require_resident),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
):
    """
    Process natural language query about finances.
    """
    trust = await fetch_trust_snapshot(wallet_address)
    runtime = build_runtime_snapshot(current_user.email, "flatwatch", trust["state"], trust["reason"], http_request)
    if not runtime.agent_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=runtime.blocked_reason or "Cursor agent runtime is unavailable.",
        )
    session_id = request.session_id or f"chat-{current_user.id}"
    existing = get_agent_session(session_id, current_user.id)
    mode = runtime.mode
    session = existing or {
        "session_id": session_id,
        "app_id": "flatwatch",
        "user_id": current_user.id,
        "subject_id": current_user.email,
        "wallet_address": wallet_address,
        "sdk_session_id": None,
        "trust_state": trust["state"],
        "mode": mode,
        "allowed_capabilities": runtime.allowed_capabilities,
        "task_type": "compat_chat",
        "context": {},
        "messages": [],
        "created_at": "",
        "updated_at": "",
    }
    session["messages"].append({"role": "user", "content": request.query, "timestamp": 0})
    session["wallet_address"] = wallet_address
    session["trust_state"] = trust["state"]
    session["mode"] = mode
    session["allowed_capabilities"] = runtime.allowed_capabilities
    _persist_chat_session(session=session, user_id=current_user.id, wallet_address=wallet_address)

    final_result = "I could not generate a response."
    latest_sdk_session_id = session["sdk_session_id"]
    estimated_cost_usd = 0.0
    async for event in stream_agent_response(session, request.query, runtime.model_dump()):
        if event["type"] == "result":
            final_result = event["content"]
            latest_sdk_session_id = event.get("sdk_session_id", latest_sdk_session_id)
            estimated_cost_usd = float(event.get("estimated_cost_usd") or 0.0)

    session["sdk_session_id"] = latest_sdk_session_id
    session["messages"].append({"role": "assistant", "content": final_result, "timestamp": 0})
    _persist_chat_session(session=session, user_id=current_user.id, wallet_address=wallet_address)
    record_usage(current_user.email, "flatwatch", estimated_cost_usd)
    return {
        "query": request.query,
        "response": final_result,
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/query-transactions")
async def query_transactions_endpoint(
    request: ChatRequest,
    current_user: User = Depends(require_resident),
):
    """
    Query transactions using natural language.
    Returns matching transactions.
    """
    transactions = await query_transactions(request.query)

    return {
        "query": request.query,
        "transactions": transactions,
        "count": len(transactions),
    }
