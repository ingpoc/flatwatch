"""Cursor SDK runtime policy for FlatWatch and portfolio agent control plane."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from fastapi import Request

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_SHARED_ROOT = _WORKSPACE_ROOT / "shared"
if str(_SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_ROOT))

from cursor_agent_runtime.policy import (  # noqa: E402
    DEFAULT_MODEL,
    resolve_runtime_policy as _resolve_cursor_policy,
)

AgentAuthMode = Literal["api_key", "unavailable", "cursor_api_key"]


@dataclass(frozen=True)
class AgentRuntimePolicy:
    runtime_available: bool
    auth_mode: AgentAuthMode
    model: str
    blocked_reason: Optional[str]


def resolve_runtime_policy(request: Optional[Request] = None) -> AgentRuntimePolicy:
    del request  # Cursor auth is API-key based.
    cursor = _resolve_cursor_policy()
    auth_mode: AgentAuthMode = (
        "api_key" if cursor.auth_mode == "cursor_api_key" else "unavailable"
    )
    return AgentRuntimePolicy(
        runtime_available=cursor.runtime_available,
        auth_mode=auth_mode,
        model=cursor.model,
        blocked_reason=cursor.blocked_reason,
    )
