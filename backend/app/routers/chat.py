# Chat router for FlatWatch
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from ..rbac import require_resident
from ..auth import User
from ..chat import query_transactions
from ..control_plane import build_entitlement_snapshot, get_agent_session, record_usage, save_agent_session
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


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    current_user: User = Depends(require_resident),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
):
    """
    Process natural language query about finances.
    """
    trust = await fetch_trust_snapshot(wallet_address)
    entitlement = build_entitlement_snapshot(current_user.email, "flatwatch", trust["state"], trust["reason"])
    if not entitlement.agent_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=entitlement.blocked_reason or "Active subscription required.",
        )
    session_id = request.session_id or f"chat-{current_user.id}"
    existing = get_agent_session(session_id, current_user.id)
    mode = "blocked" if not entitlement.agent_access else ("full" if trust["state"] == "verified" else "read_only")
    session = existing or {
        "session_id": session_id,
        "app_id": "flatwatch",
        "user_id": current_user.id,
        "subject_id": current_user.email,
        "wallet_address": wallet_address,
        "sdk_session_id": None,
        "trust_state": trust["state"],
        "mode": mode,
        "allowed_capabilities": entitlement.allowed_capabilities,
        "task_type": "compat_chat",
        "context": {},
        "messages": [],
        "created_at": "",
        "updated_at": "",
    }
    session["messages"].append({"role": "user", "content": request.query, "timestamp": 0})
    save_agent_session(
        session_id=session_id,
        app_id="flatwatch",
        user=current_user,
        subject_id=current_user.email,
        wallet_address=wallet_address,
        sdk_session_id=session["sdk_session_id"],
        trust_state=trust["state"],
        mode=mode,
        allowed_capabilities=entitlement.allowed_capabilities,
        task_type="compat_chat",
        context={},
        messages=session["messages"],
    )

    final_result = "I could not generate a response."
    latest_sdk_session_id = session["sdk_session_id"]
    async for event in stream_agent_response(session, request.query):
        if event["type"] == "result":
            final_result = event["content"]
            latest_sdk_session_id = event.get("sdk_session_id", latest_sdk_session_id)

    session["sdk_session_id"] = latest_sdk_session_id
    session["messages"].append({"role": "assistant", "content": final_result, "timestamp": 0})
    save_agent_session(
        session_id=session_id,
        app_id="flatwatch",
        user=current_user,
        subject_id=current_user.email,
        wallet_address=wallet_address,
        sdk_session_id=session["sdk_session_id"],
        trust_state=trust["state"],
        mode=mode,
        allowed_capabilities=entitlement.allowed_capabilities,
        task_type="compat_chat",
        context={},
        messages=session["messages"],
    )
    record_usage(current_user.email, "flatwatch")
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
