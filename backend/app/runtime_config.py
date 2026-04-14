from __future__ import annotations

import functools
import importlib.util
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlsplit

from fastapi import Request

AgentAuthMode = Literal["api_key", "local_cli", "bedrock", "vertex", "azure", "unavailable"]

DEFAULT_MODEL = os.getenv("CLAUDE_AGENT_MODEL", "claude-haiku-4-5-20251001")


@dataclass(frozen=True)
class AgentRuntimePolicy:
    runtime_available: bool
    auth_mode: AgentAuthMode
    model: str
    blocked_reason: Optional[str]
    claude_code_executable_path: Optional[str]


def _truthy(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _requested_auth_mode() -> str:
    normalized = (os.getenv("CLAUDE_AGENT_AUTH_MODE", "auto") or "auto").strip().lower()
    if normalized in {"api_key", "local_cli", "bedrock", "vertex", "azure"}:
        return normalized
    return "auto"


def _host_looks_local(value: Optional[str]) -> bool:
    if not value:
        return False
    host = value.split("//")[-1].split("/")[0].split(":")[0].strip().lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def _normalize_origin(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    try:
        parts = urlsplit(candidate)
        if not parts.scheme or not parts.netloc:
            return None
        return f"{parts.scheme}://{parts.netloc}".lower()
    except Exception:
        return None


@functools.lru_cache(maxsize=1)
def _allowed_origins() -> set[str]:
    return {
        origin
        for origin in (_normalize_origin(value) for value in os.getenv("CLAUDE_AGENT_ALLOWED_ORIGINS", "").split(","))
        if origin
    }


def request_matches_allowed_origin(request: Optional[Request]) -> bool:
    if request is None:
        return False

    origin = _normalize_origin(request.headers.get("origin"))
    return bool(origin and origin in _allowed_origins())


def request_looks_local(request: Optional[Request]) -> bool:
    if request is None:
        return False

    client_host = request.client.host if request.client else None
    host = request.headers.get("host")
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    forwarded_for = request.headers.get("x-forwarded-for")

    return any(
        (
            _host_looks_local(host),
            _host_looks_local(origin),
            _host_looks_local(referer),
            client_host in {"127.0.0.1", "::1"},
            forwarded_for in {"127.0.0.1", "::1"},
        )
    )


def _find_claude_code_executable() -> Optional[str]:
    explicit = os.getenv("CLAUDE_CODE_EXECUTABLE") or os.getenv("CLAUDE_CODE_PATH")
    if explicit:
        return explicit if Path(explicit).exists() else None

    discovered = shutil.which("claude")
    if discovered:
        return discovered

    fallback = Path.home() / ".claude" / "local" / "claude"
    if fallback.exists():
        return str(fallback)

    return None


def _sdk_package_available() -> bool:
    return importlib.util.find_spec("claude_agent_sdk") is not None


def resolve_runtime_policy(request: Optional[Request] = None) -> AgentRuntimePolicy:
    requested_auth_mode = _requested_auth_mode()
    has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    allow_local_cli = _truthy(os.getenv("CLAUDE_AGENT_ALLOW_LOCAL_CLI_AUTH"), True)
    local_request = request_looks_local(request)
    allowed_origin_request = request_matches_allowed_origin(request)
    cli_path = _find_claude_code_executable()

    if not _sdk_package_available():
        return AgentRuntimePolicy(
            runtime_available=False,
            auth_mode="unavailable",
            model=DEFAULT_MODEL,
            blocked_reason="claude_agent_sdk is not installed in the FlatWatch backend environment.",
            claude_code_executable_path=cli_path,
        )

    if requested_auth_mode in {"bedrock", "vertex", "azure"}:
        return AgentRuntimePolicy(
            runtime_available=True,
            auth_mode=requested_auth_mode,  # type: ignore[arg-type]
            model=DEFAULT_MODEL,
            blocked_reason=None,
            claude_code_executable_path=cli_path,
        )

    if requested_auth_mode == "api_key":
        if has_api_key:
            return AgentRuntimePolicy(
                runtime_available=True,
                auth_mode="api_key",
                model=DEFAULT_MODEL,
                blocked_reason=None,
                claude_code_executable_path=cli_path,
            )
        return AgentRuntimePolicy(
            runtime_available=False,
            auth_mode="unavailable",
            model=DEFAULT_MODEL,
            blocked_reason="ANTHROPIC_API_KEY is required for the configured runtime mode.",
            claude_code_executable_path=cli_path,
        )

    if has_api_key:
        return AgentRuntimePolicy(
            runtime_available=True,
            auth_mode="api_key",
            model=DEFAULT_MODEL,
            blocked_reason=None,
            claude_code_executable_path=cli_path,
        )

    if requested_auth_mode in {"local_cli", "auto"}:
        if not cli_path:
            return AgentRuntimePolicy(
                runtime_available=False,
                auth_mode="unavailable",
                model=DEFAULT_MODEL,
                blocked_reason="Claude Code CLI auth requires the local `claude` executable to be installed or CLAUDE_CODE_EXECUTABLE to be set.",
                claude_code_executable_path=None,
            )
        if allow_local_cli and (local_request or allowed_origin_request or request is None):
            return AgentRuntimePolicy(
                runtime_available=True,
                auth_mode="local_cli",
                model=DEFAULT_MODEL,
                blocked_reason=None,
                claude_code_executable_path=cli_path,
            )
        return AgentRuntimePolicy(
            runtime_available=False,
            auth_mode="unavailable",
            model=DEFAULT_MODEL,
            blocked_reason=(
                "Claude Code CLI auth is restricted to localhost or CLAUDE_AGENT_ALLOWED_ORIGINS. "
                "Configure an allowed frontend origin or switch to API-key/cloud-provider auth."
            ),
            claude_code_executable_path=cli_path,
        )

    return AgentRuntimePolicy(
        runtime_available=False,
        auth_mode="unavailable",
        model=DEFAULT_MODEL,
        blocked_reason="No supported Claude Agent SDK auth mode is configured.",
        claude_code_executable_path=cli_path,
    )
