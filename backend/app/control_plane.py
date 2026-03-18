import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict

from pydantic import BaseModel

from .auth import User
from .database import get_db_connection

AppId = Literal["flatwatch", "ondc-buyer", "ondc-seller"]
PortfolioTrustState = Literal[
    "no_identity",
    "identity_present_unverified",
    "verified",
    "manual_review",
    "revoked_or_blocked",
]
SubscriptionStatus = Literal["inactive", "trial", "active", "past_due", "canceled"]
SessionMode = Literal["blocked", "read_only", "full"]

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
STORE_PATH = WORKSPACE_ROOT / "shared" / "agent-control-plane" / "data" / "control-plane-store.json"


class UsageSnapshot(BaseModel):
    requests_used: int
    requests_limit: int
    period_start: str
    period_end: str
    estimated_cost_usd: float


class EntitlementSnapshot(BaseModel):
    app_id: AppId
    subscription_status: SubscriptionStatus
    plan_tier: str
    agent_access: bool
    trust_required_for_write: bool
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


class StoredEntitlementRecord(TypedDict):
    subject_id: str
    app_id: AppId
    subscription_status: SubscriptionStatus
    plan_tier: str
    requests_limit: int
    requests_used: int
    period_start: str
    period_end: str
    estimated_cost_usd: float


APP_CAPABILITIES: dict[AppId, dict[str, list[str]]] = {
    "flatwatch": {
        "read": ["transactions_query", "receipts_metadata", "challenges_summary", "bylaw_lookup"],
        "write": ["receipt_process_metadata", "challenge_create", "challenge_resolve"],
    },
    "ondc-buyer": {
        "read": ["search", "product_detail", "order_status", "trust_checkout_guidance"],
        "write": ["cart_state", "checkout_mutation"],
    },
    "ondc-seller": {
        "read": ["catalog_read", "listing_quality_analysis", "order_status", "seller_config_guidance"],
        "write": ["catalog_write", "listing_publish"],
    },
}


def _seed_entitlements(now: datetime) -> list[StoredEntitlementRecord]:
    period_end = (now + timedelta(days=30)).isoformat()
    period_start = now.isoformat()
    return [
        {
            "subject_id": "resident@flatwatch.test",
            "app_id": "flatwatch",
            "subscription_status": "active",
            "plan_tier": "pilot",
            "requests_limit": 100,
            "requests_used": 0,
            "period_start": period_start,
            "period_end": period_end,
            "estimated_cost_usd": 0.0,
        },
        {
            "subject_id": "admin@flatwatch.test",
            "app_id": "flatwatch",
            "subscription_status": "active",
            "plan_tier": "pilot",
            "requests_limit": 100,
            "requests_used": 0,
            "period_start": period_start,
            "period_end": period_end,
            "estimated_cost_usd": 0.0,
        },
    ]


def _ensure_store() -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if STORE_PATH.exists():
        return

    now = datetime.now(timezone.utc)
    STORE_PATH.write_text(json.dumps({"entitlements": _seed_entitlements(now), "sessions": []}, indent=2))


def _read_store() -> dict[str, Any]:
    _ensure_store()
    return json.loads(STORE_PATH.read_text())


def _write_store(store: dict[str, Any]) -> None:
    _ensure_store()
    STORE_PATH.write_text(json.dumps(store, indent=2))


def _default_entitlement(subject_id: str, app_id: AppId) -> StoredEntitlementRecord:
    now = datetime.now(timezone.utc)
    return {
        "subject_id": subject_id,
        "app_id": app_id,
        "subscription_status": "inactive",
        "plan_tier": "free",
        "requests_limit": 0,
        "requests_used": 0,
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat(),
        "estimated_cost_usd": 0.0,
    }


def get_or_create_entitlement(subject_id: str, app_id: AppId) -> StoredEntitlementRecord:
    store = _read_store()
    for record in store["entitlements"]:
        if record["subject_id"] == subject_id and record["app_id"] == app_id:
            return record

    record = _default_entitlement(subject_id, app_id)
    store["entitlements"].append(record)
    _write_store(store)
    return record


def _subscription_blocked_reason(status: SubscriptionStatus) -> Optional[str]:
    if status == "past_due":
        return "Subscription payment is past due."
    if status == "canceled":
        return "Subscription was canceled."
    if status == "inactive":
        return "Active subscription required."
    return None


def _mode_for(subscription_status: SubscriptionStatus, trust_state: PortfolioTrustState) -> SessionMode:
    if subscription_status not in {"active", "trial"}:
        return "blocked"
    if trust_state == "verified":
        return "full"
    return "read_only"


def _allowed_capabilities(app_id: AppId, mode: SessionMode) -> list[str]:
    if mode == "blocked":
        return []
    if mode == "read_only":
        return APP_CAPABILITIES[app_id]["read"]
    return APP_CAPABILITIES[app_id]["read"] + APP_CAPABILITIES[app_id]["write"]


def build_entitlement_snapshot(
    subject_id: str,
    app_id: AppId,
    trust_state: PortfolioTrustState,
    trust_reason: Optional[str],
) -> EntitlementSnapshot:
    record = get_or_create_entitlement(subject_id, app_id)
    mode = _mode_for(record["subscription_status"], trust_state)
    usage_exhausted = record["requests_limit"] > 0 and record["requests_used"] >= record["requests_limit"]
    blocked_reason = _subscription_blocked_reason(record["subscription_status"])

    if blocked_reason is None and mode == "read_only" and trust_state != "verified":
        blocked_reason = trust_reason or "Trust verification required for write actions."

    if usage_exhausted:
        blocked_reason = "Usage limit exhausted for current billing period."

    return EntitlementSnapshot(
        app_id=app_id,
        subscription_status=record["subscription_status"],
        plan_tier=record["plan_tier"],
        agent_access=mode != "blocked" and not usage_exhausted,
        trust_required_for_write=True,
        usage=UsageSnapshot(
            requests_used=record["requests_used"],
            requests_limit=record["requests_limit"],
            period_start=record["period_start"],
            period_end=record["period_end"],
            estimated_cost_usd=record["estimated_cost_usd"],
        ),
        allowed_capabilities=_allowed_capabilities(app_id, mode),
        blocked_reason=blocked_reason,
    )


def record_usage(subject_id: str, app_id: AppId, incremental_cost_usd: float = 0.0) -> UsageSnapshot:
    store = _read_store()
    updated: Optional[StoredEntitlementRecord] = None

    for record in store["entitlements"]:
        if record["subject_id"] == subject_id and record["app_id"] == app_id:
            record["requests_used"] += 1
            record["estimated_cost_usd"] = round(record["estimated_cost_usd"] + incremental_cost_usd, 6)
            updated = record
            break

    if updated is None:
        updated = _default_entitlement(subject_id, app_id)
        updated["requests_used"] = 1
        updated["estimated_cost_usd"] = round(incremental_cost_usd, 6)
        store["entitlements"].append(updated)

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
    user: User,
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
    conn = get_db_connection()
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute(
        "SELECT created_at FROM agent_sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    created_at = existing["created_at"] if existing else now

    conn.execute(
        """
        INSERT OR REPLACE INTO agent_sessions (
            session_id, app_id, user_id, subject_id, wallet_address, sdk_session_id,
            trust_state, mode, allowed_capabilities, task_type, context_json, messages_json,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            app_id,
            user.id,
            subject_id,
            wallet_address,
            sdk_session_id,
            trust_state,
            mode,
            json.dumps(allowed_capabilities),
            task_type,
            json.dumps(context),
            json.dumps(messages),
            created_at,
            now,
        ),
    )
    conn.commit()
    conn.close()

    return AgentSessionSummary(
        app_id=app_id,
        session_id=session_id,
        sdk_session_id=sdk_session_id,
        subject_id=subject_id,
        trust_state=trust_state,
        mode=mode,
        allowed_capabilities=allowed_capabilities,
        created_at=created_at,
        updated_at=now,
    )


def get_agent_session(session_id: str, user_id: int) -> Optional[dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM agent_sessions WHERE session_id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "session_id": row["session_id"],
        "app_id": row["app_id"],
        "user_id": row["user_id"],
        "subject_id": row["subject_id"],
        "wallet_address": row["wallet_address"],
        "sdk_session_id": row["sdk_session_id"],
        "trust_state": row["trust_state"],
        "mode": row["mode"],
        "allowed_capabilities": json.loads(row["allowed_capabilities"]),
        "task_type": row["task_type"],
        "context": json.loads(row["context_json"]),
        "messages": json.loads(row["messages_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
