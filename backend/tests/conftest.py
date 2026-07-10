import os
from pathlib import Path

import pytest


# Keep pytest runs off the live dev database so local browser/runtime flows remain intact.
os.environ.setdefault(
    "FLATWATCH_DATABASE_PATH",
    str((Path(__file__).parent / ".tmp" / "flatwatch-test.db").resolve()),
)


@pytest.fixture(autouse=True)
def mock_trust_lookup(monkeypatch):
    """Default trust lookup: verified when X-Wallet-Address is present, else no_identity."""

    async def _fetch(wallet_address):
        if not wallet_address:
            return {
                "state": "no_identity",
                "eligible": False,
                "reason": "Connect a wallet-backed AadhaarChain identity before using trust-gated flows.",
            }
        return {
            "state": "verified",
            "eligible": True,
            "reason": None,
        }

    monkeypatch.setattr("app.trust.fetch_trust_snapshot", _fetch)


@pytest.fixture
def verified_wallet_headers():
    return {"X-Wallet-Address": "FlatWatchTestWallet111111111111111111111"}
