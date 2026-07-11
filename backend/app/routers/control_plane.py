# Control-plane router for runtime status and agent sessions
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pydantic import BaseModel

from ..agent_runtime import stream_agent_response
from ..auth import User
from ..control_plane import (
    AgentMessageRequest,
    AgentRuntimeSnapshot,
    AgentSessionCreateRequest,
    AppId,
    build_runtime_snapshot,
    get_agent_session,
    record_usage,
    save_agent_session,
)
from ..rbac import require_resident
from ..trust import fetch_trust_snapshot

router = APIRouter(tags=["Control Plane"])
_portfolio_bearer = HTTPBearer(auto_error=False)


async def _resolve_subject_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_portfolio_bearer),
) -> str:
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id or bearer token is required.",
        )
    user = await require_resident(credentials)
    return user.email


@router.get("/api/agent/runtime")
async def get_runtime(
    app: AppId,
    request: Request,
    subject_id: str = Depends(_resolve_subject_id),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
):
    trust = await fetch_trust_snapshot(wallet_address)
    return {
        **build_runtime_snapshot(subject_id, app, trust["state"], trust["reason"], request).model_dump(),
        "compatibility_surface": "agent_runtime",
    }


def _persist_runtime_session(
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


@router.get("/api/entitlements/me")
async def get_runtime_compat(
    app: AppId,
    request: Request,
    current_user: User = Depends(require_resident),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
):
    trust = await fetch_trust_snapshot(wallet_address)
    return {
        **build_runtime_snapshot(current_user.email, app, trust["state"], trust["reason"], request).model_dump(),
        "compatibility_surface": "agent_runtime",
    }


@router.post("/api/agent/flatwatch/sessions")
async def create_agent_session(
    request: AgentSessionCreateRequest,
    http_request: Request,
    current_user: User = Depends(require_resident),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
):
    trust = await fetch_trust_snapshot(wallet_address)
    runtime = build_runtime_snapshot(current_user.email, "flatwatch", trust["state"], trust["reason"], http_request)
    if not runtime.agent_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=runtime.blocked_reason or "Cursor agent runtime is unavailable.",
        )
    session_id = request.resume_session_id or f"session-{datetime.now(timezone.utc).timestamp():.0f}"
    return save_agent_session(
        session_id=session_id,
        app_id="flatwatch",
        user_id=current_user.id,
        subject_id=current_user.email,
        wallet_address=wallet_address,
        sdk_session_id=None,
        trust_state=trust["state"],
        mode=runtime.mode,
        allowed_capabilities=runtime.allowed_capabilities,
        task_type=request.task_type,
        context=request.context,
        messages=[],
    )


@router.get("/api/agent/flatwatch/sessions/{session_id}")
async def get_session_summary(
    session_id: str,
    current_user: User = Depends(require_resident),
):
    session = get_agent_session(session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.post("/api/agent/flatwatch/messages")
async def send_agent_message(
    request: AgentMessageRequest,
    http_request: Request,
    current_user: User = Depends(require_resident),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
):
    session = get_agent_session(request.session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    trust = await fetch_trust_snapshot(wallet_address or session.get("wallet_address"))
    runtime = build_runtime_snapshot(current_user.email, "flatwatch", trust["state"], trust["reason"], http_request)
    if not runtime.agent_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=runtime.blocked_reason or "Cursor agent runtime is unavailable.",
        )

    session["messages"].append({"role": "user", "content": request.message, "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)})
    session["wallet_address"] = wallet_address or session.get("wallet_address")
    session["trust_state"] = trust["state"]
    session["mode"] = runtime.mode
    session["allowed_capabilities"] = runtime.allowed_capabilities
    _persist_runtime_session(session=session, user_id=current_user.id, wallet_address=session["wallet_address"])

    async def event_stream():
        final_result: Optional[str] = None
        latest_sdk_session_id = session["sdk_session_id"]
        estimated_cost_usd = 0.0
        async for event in stream_agent_response(session, request.message, runtime.model_dump()):
            if event["type"] == "result":
                final_result = event["content"]
                latest_sdk_session_id = event.get("sdk_session_id", latest_sdk_session_id)
                estimated_cost_usd = float(event.get("estimated_cost_usd") or 0.0)
            yield f"data: {json.dumps(event)}\n\n"

        session["sdk_session_id"] = latest_sdk_session_id
        session["wallet_address"] = wallet_address or session.get("wallet_address")
        session["trust_state"] = trust["state"]
        session["mode"] = runtime.mode
        session["allowed_capabilities"] = runtime.allowed_capabilities
        if final_result:
            session["messages"].append({"role": "assistant", "content": final_result, "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)})
            usage = record_usage(current_user.email, "flatwatch", estimated_cost_usd)
            yield f"data: {json.dumps({'type': 'usage', 'usage': usage.model_dump(), 'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000)})}\n\n"

        _persist_runtime_session(session=session, user_id=current_user.id, wallet_address=session["wallet_address"])

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class PortfolioAgentRequest(BaseModel):
    prompt: str
    sessionId: str
    context: dict[str, Any] = {}


_ONDC_AGENT_SESSIONS: dict[str, dict[str, Any]] = {}


async def _portfolio_runtime_snapshot(
    *,
    app_id: AppId,
    subject_id: str,
    wallet_address: Optional[str],
    request: Request,
) -> AgentRuntimeSnapshot:
    trust = await fetch_trust_snapshot(wallet_address)
    return build_runtime_snapshot(subject_id, app_id, trust["state"], trust["reason"], request)


def _portfolio_session_key(app_id: AppId, session_id: str) -> str:
    return f"{app_id}:{session_id}"


async def _portfolio_agent_stream(
    *,
    app_id: AppId,
    subject_id: str,
    wallet_address: Optional[str],
    request: Request,
    body: PortfolioAgentRequest,
):
    runtime = await _portfolio_runtime_snapshot(
        app_id=app_id,
        subject_id=subject_id,
        wallet_address=wallet_address,
        request=request,
    )
    if not runtime.agent_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=runtime.blocked_reason or "Cursor agent runtime is unavailable.",
        )

    session_key = _portfolio_session_key(app_id, body.sessionId)
    session = _ONDC_AGENT_SESSIONS.get(session_key)
    if session is None:
        session = {
            "session_id": body.sessionId,
            "app_id": app_id,
            "subject_id": subject_id,
            "wallet_address": wallet_address,
            "sdk_session_id": None,
            "trust_state": runtime.trust_state,
            "mode": runtime.mode,
            "allowed_capabilities": runtime.allowed_capabilities,
            "task_type": f"{app_id}-chat",
            "context": body.context,
            "messages": [],
        }
        _ONDC_AGENT_SESSIONS[session_key] = session

    async def event_stream():
        final_result: Optional[str] = None
        latest_sdk_session_id = session.get("sdk_session_id")
        estimated_cost_usd = 0.0
        async for event in stream_agent_response(session, body.prompt, runtime.model_dump()):
            if event["type"] == "result":
                final_result = event["content"]
                latest_sdk_session_id = event.get("sdk_session_id", latest_sdk_session_id)
                estimated_cost_usd = float(event.get("estimated_cost_usd") or 0.0)
            yield f"data: {json.dumps(event)}\n\n"

        session["sdk_session_id"] = latest_sdk_session_id
        if final_result:
            session["messages"].append(
                {"role": "assistant", "content": final_result, "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)}
            )
            usage = record_usage(subject_id, app_id, estimated_cost_usd)
            yield f"data: {json.dumps({'type': 'usage', 'usage': usage.model_dump(), 'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.post("/api/agent/buyer")
async def portfolio_buyer_agent(
    body: PortfolioAgentRequest,
    request: Request,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
):
    subject_id = (x_user_id or "").strip()
    if not subject_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-Id is required.")
    return await _portfolio_agent_stream(
        app_id="ondc-buyer",
        subject_id=subject_id,
        wallet_address=wallet_address,
        request=request,
        body=body,
    )


@router.post("/api/agent/seller")
async def portfolio_seller_agent(
    body: PortfolioAgentRequest,
    request: Request,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
):
    subject_id = (x_user_id or "").strip()
    if not subject_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-Id is required.")
    return await _portfolio_agent_stream(
        app_id="ondc-seller",
        subject_id=subject_id,
        wallet_address=wallet_address,
        request=request,
        body=body,
    )
