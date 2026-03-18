from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict

from fastapi import Request
from pydantic import BaseModel

from .runtime_config import AgentAuthMode, resolve_runtime_policy

AppId = Literal["flatwatch", "ondc-buyer", "ondc-seller"]
PortfolioTrustState = Literal[
    "no_identity",
    "identity_present_unverified",
    "verified",
    "manual_review",
    "revoked_or_blocked",
]
SessionMode = Literal["blocked", "read_only", "full"]

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
STORE_PATH = WORKSPACE_ROOT / "shared" / "agent-control-plane" / "data" / "control-plane-store.json"


class UsageSnapshot(BaseModel):
    requests_used: int
    requests_limit: int
    period_start: str
    period_end: str
    estimated_cost_usd: float


class AgentRuntimeSnapshot(BaseModel):
    app_id: AppId
    auth_mode: AgentAuthMode
    model: str
    runtime_available: bool
    agent_access: bool
    trust_state: PortfolioTrustState
    trust_required_for_write: bool
    mode: SessionMode
    usage: UsageSnapshot
    allowed_capabilities: list[str]
    blocked_reason: Optional[str] = None


class AgentSessionSummary(BaseModel):
    app_id: AppId
    session_id: str
    sdk_session_id: Optional[str] = None
    subject_id: str
    trust_state: PortfolioTrustState
    mode: SessionMode
    allowed_capabilities: list[str]
    created_at: str
    updated_at: str


class AgentSessionCreateRequest(BaseModel):
    task_type: str
    context: dict[str, Any]
    resume_session_id: Optional[str] = None


class AgentMessageRequest(BaseModel):
    session_id: str
    message: str


class StoredUsageRecord(TypedDict):
    subject_id: str
    app_id: AppId
    requests_used: int
    requests_limit: int
    period_start: str
    period_end: str
    estimated_cost_usd: float


class StoredSessionRecord(TypedDict):
    session_id: str
    app_id: AppId
    subject_id: str
    wallet_address: Optional[str]
    sdk_session_id: Optional[str]
    trust_state: PortfolioTrustState
    mode: SessionMode
    allowed_capabilities: list[str]
    task_type: str
    context: dict[str, Any]
    messages: list[dict[str, Any]]
    created_at: str
    updated_at: str


class ControlPlaneStore(TypedDict, total=False):
    usage: list[StoredUsageRecord]
    sessions: list[StoredSessionRecord]
    entitlements: list[dict[str, Any]]


APP_CAPABILITIES: dict[AppId, dict[str, list[str]]] = {
    "flatwatch": {
        "read": ["transactions_query", "receipts_metadata", "challenges_summary", "bylaw_lookup"],
        "write": ["receipt_process_metadata", "challenge_create", "challenge_resolve"],
    },
    "ondc-buyer": {
        "read": ["search", "product_detail", "cart_state", "order_status", "trust_checkout_guidance"],
        "write": ["checkout_mutation"],
    },
    "ondc-seller": {
        "read": ["catalog_read", "listing_quality_analysis", "order_status", "seller_config_guidance"],
        "write": ["catalog_write", "listing_publish"],
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_period_end() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()


def _default_usage(subject_id: str, app_id: AppId) -> StoredUsageRecord:
    return {
        "subject_id": subject_id,
        "app_id": app_id,
        "requests_used": 0,
        "requests_limit": 0,
        "period_start": _now_iso(),
        "period_end": _default_period_end(),
        "estimated_cost_usd": 0.0,
    }


def _ensure_store() -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        STORE_PATH.write_text(json.dumps({"usage": [], "sessions": []}, indent=2))


def _normalize_usage(record: dict[str, Any]) -> Optional[StoredUsageRecord]:
    subject_id = record.get("subject_id")
    app_id = record.get("app_id")
    if not isinstance(subject_id, str) or app_id not in {"flatwatch", "ondc-buyer", "ondc-seller"}:
        return None

    return {
        "subject_id": subject_id,
        "app_id": app_id,
        "requests_used": int(record.get("requests_used", 0) or 0),
        "requests_limit": int(record.get("requests_limit", 0) or 0),
        "period_start": record.get("period_start") or _now_iso(),
        "period_end": record.get("period_end") or _default_period_end(),
        "estimated_cost_usd": float(record.get("estimated_cost_usd", 0.0) or 0.0),
    }


def _read_store() -> ControlPlaneStore:
    _ensure_store()
    raw = json.loads(STORE_PATH.read_text())
    usage_source = raw.get("usage") or raw.get("entitlements") or []
    usage = [
        normalized
        for normalized in (_normalize_usage(record) for record in usage_source if isinstance(record, dict))
        if normalized is not None
    ]
    sessions = raw.get("sessions") if isinstance(raw.get("sessions"), list) else []
    return {
        "usage": usage,
        "sessions": sessions,
    }


def _write_store(store: ControlPlaneStore) -> None:
    _ensure_store()
    STORE_PATH.write_text(json.dumps({"usage": store.get("usage", []), "sessions": store.get("sessions", [])}, indent=2))


def get_or_create_usage(subject_id: str, app_id: AppId) -> StoredUsageRecord:
    store = _read_store()
    for record in store.get("usage", []):
        if record["subject_id"] == subject_id and record["app_id"] == app_id:
            return record

    record = _default_usage(subject_id, app_id)
    store.setdefault("usage", []).append(record)
    _write_store(store)
    return record


def build_runtime_snapshot(
    subject_id: str,
    app_id: AppId,
    trust_state: PortfolioTrustState,
    trust_reason: Optional[str],
    request: Optional[Request] = None,
) -> AgentRuntimeSnapshot:
    usage = get_or_create_usage(subject_id, app_id)
    runtime_policy = resolve_runtime_policy(request)
    if not runtime_policy.runtime_available:
        mode: SessionMode = "blocked"
    elif trust_state == "verified":
        mode = "full"
    else:
        mode = "read_only"

    blocked_reason = runtime_policy.blocked_reason
    if blocked_reason is None and mode == "read_only":
        blocked_reason = trust_reason or "Trust verification is still required for higher-trust write actions."

    if mode == "blocked":
        allowed_capabilities: list[str] = []
    elif mode == "read_only":
        allowed_capabilities = APP_CAPABILITIES[app_id]["read"]
    else:
        allowed_capabilities = APP_CAPABILITIES[app_id]["read"] + APP_CAPABILITIES[app_id]["write"]

    return AgentRuntimeSnapshot(
        app_id=app_id,
        auth_mode=runtime_policy.auth_mode,
        model=runtime_policy.model,
        runtime_available=runtime_policy.runtime_available,
        agent_access=runtime_policy.runtime_available,
        trust_state=trust_state,
        trust_required_for_write=True,
        mode=mode,
        usage=UsageSnapshot(
            requests_used=usage["requests_used"],
            requests_limit=usage["requests_limit"],
            period_start=usage["period_start"],
            period_end=usage["period_end"],
            estimated_cost_usd=usage["estimated_cost_usd"],
        ),
        allowed_capabilities=allowed_capabilities,
        blocked_reason=blocked_reason,
    )


def record_usage(subject_id: str, app_id: AppId, incremental_cost_usd: float = 0.0) -> UsageSnapshot:
    store = _read_store()
    updated: Optional[StoredUsageRecord] = None

    for record in store.get("usage", []):
        if record["subject_id"] == subject_id and record["app_id"] == app_id:
            record["requests_used"] += 1
            record["estimated_cost_usd"] = round(record["estimated_cost_usd"] + incremental_cost_usd, 6)
            updated = record
            break

    if updated is None:
        updated = _default_usage(subject_id, app_id)
        updated["requests_used"] = 1
        updated["estimated_cost_usd"] = round(incremental_cost_usd, 6)
        store.setdefault("usage", []).append(updated)

    _write_store(store)
    return UsageSnapshot(
        requests_used=updated["requests_used"],
        requests_limit=updated["requests_limit"],
        period_start=updated["period_start"],
        period_end=updated["period_end"],
        estimated_cost_usd=updated["estimated_cost_usd"],
    )


def save_agent_session(
    *,
    session_id: str,
    app_id: AppId,
    subject_id: str,
    wallet_address: Optional[str],
    sdk_session_id: Optional[str],
    trust_state: PortfolioTrustState,
    mode: SessionMode,
    allowed_capabilities: list[str],
    task_type: str,
    context: dict[str, Any],
    messages: list[dict[str, Any]],
) -> AgentSessionSummary:
    store = _read_store()
    timestamp = _now_iso()
    existing = next(
        (
            item
            for item in store.get("sessions", [])
            if item["session_id"] == session_id and item["app_id"] == app_id and item["subject_id"] == subject_id
        ),
        None,
    )

    if existing is None:
        existing = {
            "session_id": session_id,
            "app_id": app_id,
            "subject_id": subject_id,
            "wallet_address": wallet_address,
            "sdk_session_id": sdk_session_id,
            "trust_state": trust_state,
            "mode": mode,
            "allowed_capabilities": allowed_capabilities,
            "task_type": task_type,
            "context": context,
            "messages": messages,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        store.setdefault("sessions", []).append(existing)
    else:
        existing.update(
            {
                "wallet_address": wallet_address,
                "sdk_session_id": sdk_session_id,
                "trust_state": trust_state,
                "mode": mode,
                "allowed_capabilities": allowed_capabilities,
                "task_type": task_type,
                "context": context,
                "messages": messages,
                "updated_at": timestamp,
            }
        )

    _write_store(store)
    return AgentSessionSummary(
        app_id=app_id,
        session_id=existing["session_id"],
        sdk_session_id=existing.get("sdk_session_id"),
        subject_id=existing["subject_id"],
        trust_state=existing["trust_state"],
        mode=existing["mode"],
        allowed_capabilities=existing["allowed_capabilities"],
        created_at=existing["created_at"],
        updated_at=existing["updated_at"],
    )


def get_agent_session(session_id: str, subject_id: str) -> Optional[StoredSessionRecord]:
    store = _read_store()
    for session in store.get("sessions", []):
        if session["session_id"] == session_id and session["subject_id"] == subject_id:
            return session
    return None
