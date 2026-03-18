# Control-plane router for entitlements and agent sessions
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from ..agent_runtime import stream_agent_response
from ..auth import User
from ..control_plane import (
    AgentMessageRequest,
    AgentSessionCreateRequest,
    AppId,
    build_entitlement_snapshot,
    get_agent_session,
    record_usage,
    save_agent_session,
)
from ..rbac import require_resident
from ..trust import fetch_trust_snapshot

router = APIRouter(tags=["Control Plane"])


def _mode_for(entitlement_access: bool, trust_state: str) -> str:
    if not entitlement_access:
        return "blocked"
    if trust_state == "verified":
        return "full"
    return "read_only"


@router.get("/api/entitlements/me")
async def get_entitlement(
    app: AppId,
    current_user: User = Depends(require_resident),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
):
    trust = await fetch_trust_snapshot(wallet_address)
    return build_entitlement_snapshot(current_user.email, app, trust["state"], trust["reason"])


@router.post("/api/agent/flatwatch/sessions")
async def create_agent_session(
    request: AgentSessionCreateRequest,
    current_user: User = Depends(require_resident),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
):
    trust = await fetch_trust_snapshot(wallet_address)
    entitlement = build_entitlement_snapshot(current_user.email, "flatwatch", trust["state"], trust["reason"])
    if not entitlement.agent_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=entitlement.blocked_reason or "Active subscription required.",
        )
    session_id = request.resume_session_id or f"session-{datetime.now(timezone.utc).timestamp():.0f}"
    mode = _mode_for(entitlement.agent_access, trust["state"])
    return save_agent_session(
        session_id=session_id,
        app_id="flatwatch",
        user=current_user,
        subject_id=current_user.email,
        wallet_address=wallet_address,
        sdk_session_id=None,
        trust_state=trust["state"],
        mode=mode,
        allowed_capabilities=entitlement.allowed_capabilities,
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
    current_user: User = Depends(require_resident),
):
    session = get_agent_session(request.session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session["messages"].append({"role": "user", "content": request.message, "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)})
    save_agent_session(
        session_id=session["session_id"],
        app_id="flatwatch",
        user=current_user,
        subject_id=session["subject_id"],
        wallet_address=session["wallet_address"],
        sdk_session_id=session["sdk_session_id"],
        trust_state=session["trust_state"],
        mode=session["mode"],
        allowed_capabilities=session["allowed_capabilities"],
        task_type=session["task_type"],
        context=session["context"],
        messages=session["messages"],
    )

    async def event_stream():
        final_result: Optional[str] = None
        latest_sdk_session_id = session["sdk_session_id"]
        async for event in stream_agent_response(session, request.message):
            if event["type"] == "result":
                final_result = event["content"]
                latest_sdk_session_id = event.get("sdk_session_id", latest_sdk_session_id)
            yield f"data: {json.dumps(event)}\n\n"

        session["sdk_session_id"] = latest_sdk_session_id
        if final_result:
            session["messages"].append({"role": "assistant", "content": final_result, "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)})
            usage = record_usage(current_user.email, "flatwatch")
            yield f"data: {json.dumps({'type': 'usage', 'usage': usage.model_dump(), 'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000)})}\n\n"

        save_agent_session(
            session_id=session["session_id"],
            app_id="flatwatch",
            user=current_user,
            subject_id=session["subject_id"],
            wallet_address=session["wallet_address"],
            sdk_session_id=session["sdk_session_id"],
            trust_state=session["trust_state"],
            mode=session["mode"],
            allowed_capabilities=session["allowed_capabilities"],
            task_type=session["task_type"],
            context=session["context"],
            messages=session["messages"],
        )

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
