import logging
import os
from typing import Optional, TypedDict

import httpx
from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)


class TrustSnapshot(TypedDict):
    state: str
    eligible: bool
    reason: Optional[str]

TRUST_API_URL = os.getenv("TRUST_API_URL", "http://127.0.0.1:43101")


async def fetch_trust_snapshot(wallet_address: Optional[str]) -> TrustSnapshot:
    if not wallet_address:
        return {
            "state": "no_identity",
            "eligible": False,
            "reason": "Connect a wallet-backed AadhaarChain identity before using trust-gated flows.",
        }

    try:
        async with httpx.AsyncClient() as client:
            identity_response = await client.get(f"{TRUST_API_URL}/api/identity/{wallet_address}", timeout=10.0)
            identity_response.raise_for_status()
            identity_data = identity_response.json()
            if not identity_data.get("data"):
                return {
                    "state": "no_identity",
                    "eligible": False,
                    "reason": "Create an identity anchor in AadhaarChain before continuing.",
                }

            trust_response = await client.get(f"{TRUST_API_URL}/api/identity/{wallet_address}/trust", timeout=10.0)
            trust_response.raise_for_status()
            trust_data = trust_response.json()["data"]
            return {
                "state": trust_data["trust_state"],
                "eligible": trust_data["high_trust_eligible"],
                "reason": trust_data.get("state_reason"),
            }
    except httpx.RequestError:
        logger.warning("Trust service request failed for wallet %s", wallet_address, exc_info=True)
        return {
            "state": "no_identity",
            "eligible": False,
            "reason": "Could not connect to the trust service.",
        }
    except Exception:
        logger.exception("Unexpected trust lookup failure for wallet %s", wallet_address)
        return {
            "state": "no_identity",
            "eligible": False,
            "reason": "An unexpected error occurred while fetching trust status.",
        }


async def require_verified_wallet_trust(
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
) -> TrustSnapshot:
    """Server-side gate for elevated FlatWatch writes (receipts, OCR, challenges)."""
    trust = await fetch_trust_snapshot(x_wallet_address)
    if not trust["eligible"] or trust["state"] != "verified":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=trust["reason"]
            or "Verified AadhaarChain trust is required for this elevated FlatWatch action.",
        )
    return trust
