import os
from typing import Optional, TypedDict

import httpx

class TrustSnapshot(TypedDict):
    state: str
    eligible: bool
    reason: Optional[str]

TRUST_API_URL = os.getenv("TRUST_API_URL", "http://127.0.0.1:8000")


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
    except Exception as error:
        return {
            "state": "no_identity",
            "eligible": False,
            "reason": str(error),
        }
