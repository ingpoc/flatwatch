"""FlatWatch dual-control proposals — AgentGuard-style two-party approval.

PII-free proposals for consequential payment/correction actions.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

STATE_FILE = "flatwatch-dual-control.json"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class DualProposal(BaseModel):
    proposal_id: str
    action: str
    amount_inr: float = 0
    resource_id: str
    created_by: str
    status: Literal["pending", "approved", "rejected", "executed"] = "pending"
    approvals: list[str] = Field(default_factory=list)
    required_approvals: int = 2
    created_at: str
    updated_at: str
    note: str = ""


class DualControlState(BaseModel):
    version: int = 1
    proposals: dict[str, DualProposal] = Field(default_factory=dict)


def _path(data_dir: str) -> Path:
    return Path(data_dir).expanduser() / STATE_FILE


def load_state(data_dir: str) -> DualControlState:
    path = _path(data_dir)
    if not path.is_file():
        return DualControlState()
    return DualControlState.model_validate(json.loads(path.read_text(encoding="utf-8") or "{}"))


def save_state(data_dir: str, state: DualControlState) -> None:
    path = _path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(path)


def create_proposal(
    data_dir: str,
    *,
    action: str,
    resource_id: str,
    created_by: str,
    amount_inr: float = 0,
    note: str = "",
) -> DualProposal:
    state = load_state(data_dir)
    now = _utcnow()
    proposal = DualProposal(
        proposal_id=f"prop_{uuid.uuid4().hex[:12]}",
        action=action,
        amount_inr=amount_inr,
        resource_id=resource_id,
        created_by=created_by,
        status="pending",
        approvals=[],
        required_approvals=2,
        created_at=now,
        updated_at=now,
        note=note,
    )
    state.proposals[proposal.proposal_id] = proposal
    save_state(data_dir, state)
    return proposal


def approve_proposal(
    data_dir: str,
    *,
    proposal_id: str,
    approver: str,
) -> DualProposal:
    state = load_state(data_dir)
    proposal = state.proposals.get(proposal_id)
    if not proposal:
        raise KeyError(f"Unknown proposal: {proposal_id}")
    if proposal.status not in {"pending", "approved"}:
        raise ValueError(f"Proposal not approvable: {proposal.status}")
    if approver in proposal.approvals:
        raise ConflictError("Approver already signed this proposal (replay rejected).")
    approvals = [*proposal.approvals, approver]
    status: Literal["pending", "approved", "rejected", "executed"] = (
        "approved" if len(approvals) >= proposal.required_approvals else "pending"
    )
    proposal = proposal.model_copy(
        update={
            "approvals": approvals,
            "status": status,
            "updated_at": _utcnow(),
        }
    )
    state.proposals[proposal_id] = proposal
    save_state(data_dir, state)
    return proposal


def get_proposal(data_dir: str, proposal_id: str) -> Optional[DualProposal]:
    return load_state(data_dir).proposals.get(proposal_id)


class ConflictError(Exception):
    pass
