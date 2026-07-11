"""Unit tests for FlatWatch dual-control proposals."""
from __future__ import annotations

from pathlib import Path

import pytest

from app import dual_control


def test_dual_control_requires_two_approvers(tmp_path: Path) -> None:
    data_dir = str(tmp_path)
    proposal = dual_control.create_proposal(
        data_dir,
        action="payment_proposal",
        resource_id="txn-1",
        created_by="treasurer",
        amount_inr=2500,
        note="Water bill",
    )
    assert proposal.status == "pending"
    first = dual_control.approve_proposal(
        data_dir, proposal_id=proposal.proposal_id, approver="member-a"
    )
    assert first.status == "pending"
    assert len(first.approvals) == 1
    second = dual_control.approve_proposal(
        data_dir, proposal_id=proposal.proposal_id, approver="member-b"
    )
    assert second.status == "approved"
    assert len(second.approvals) == 2
    with pytest.raises(dual_control.ConflictError):
        dual_control.approve_proposal(
            data_dir, proposal_id=proposal.proposal_id, approver="member-a"
        )
