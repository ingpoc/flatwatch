"""Dual-control proposal API for FlatWatch consequential actions."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..dual_control import (
    ConflictError,
    approve_proposal,
    create_proposal,
    get_proposal,
)

router = APIRouter(prefix="/api/dual-control", tags=["Dual Control"])

DATA_DIR = os.getenv(
    "FLATWATCH_DATA_DIR",
    str(Path(__file__).resolve().parents[2] / "data"),
)


class CreateProposalBody(BaseModel):
    action: str = Field(..., min_length=1)
    resource_id: str = Field(..., min_length=1)
    created_by: str = Field(..., min_length=1)
    amount_inr: float = 0
    note: str = ""


class ApproveBody(BaseModel):
    approver: str = Field(..., min_length=1)


@router.post("/proposals")
def create_proposal_route(body: CreateProposalBody):
    proposal = create_proposal(
        DATA_DIR,
        action=body.action,
        resource_id=body.resource_id,
        created_by=body.created_by,
        amount_inr=body.amount_inr,
        note=body.note,
    )
    return {"success": True, "proposal": proposal.model_dump()}


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal_route(proposal_id: str, body: ApproveBody):
    try:
        proposal = approve_proposal(
            DATA_DIR,
            proposal_id=proposal_id,
            approver=body.approver,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "proposal": proposal.model_dump()}


@router.get("/proposals/{proposal_id}")
def get_proposal_route(proposal_id: str):
    proposal = get_proposal(DATA_DIR, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Unknown proposal")
    return {"success": True, "proposal": proposal.model_dump()}
