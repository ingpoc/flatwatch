# OCR integration for FlatWatch (POC mock)
from datetime import datetime
from typing import Optional
import hashlib
import os
import re
import httpx


class ReceiptData:
    """Extracted receipt data."""

    def __init__(
        self,
        amount: float,
        date: str,
        vendor: str,
        confidence: float = 0.9,
    ):
        self.amount = amount
        self.date = date
        self.vendor = vendor
        self.confidence = confidence


class OCRClient:
    """Mock OCR client for POC."""

    def __init__(self, api_key: str = None):
        """Initialize client (POC: no credentials needed)."""
        self.api_key = api_key or "mock_key"

    async def extract_from_file(self, file_path: str) -> ReceiptData:
        """
        Extract data from receipt file (POC mock).
        In production, this will call Google Cloud Vision or Tesseract.
        """
        # Mock extraction based on filename patterns
        filename = file_path.lower()

        # Extract mock data
        if "water" in filename or "bill" in filename:
            return ReceiptData(
                amount=8500.0,
                date="2025-01-20",
                vendor="Water Supply Co",
                confidence=0.92,
            )
        elif "maintenance" in filename:
            return ReceiptData(
                amount=6000.0,
                date="2025-01-15",
                vendor="Society Maintenance",
                confidence=0.88,
            )
        elif "lift" in filename:
            return ReceiptData(
                amount=15000.0,
                date="2025-01-18",
                vendor="Lift Maintenance Service",
                confidence=0.85,
            )
        else:
            # Default mock data
            return ReceiptData(
                amount=5000.0,
                date=datetime.now().strftime("%Y-%m-%d"),
                vendor="Unknown Vendor",
                confidence=0.75,
            )


async def extract_receipt_data(file_path: str) -> dict:
    """
    Extract data from receipt file.
    Returns extracted data with confidence score.
    """
    provider_url = os.getenv("FLATWATCH_OCR_PROVIDER_URL")
    if provider_url:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(provider_url, json={"file_reference": file_path})
            response.raise_for_status()
            payload = response.json()
        return {
            "amount": float(payload["amount"]),
            "date": payload["date"],
            "vendor": payload["vendor"],
            "confidence": float(payload.get("confidence", 0)),
            "extraction_method": payload.get("extraction_method", "provider_api"),
            "source_hash": hashlib.sha256(file_path.encode("utf-8")).hexdigest(),
            "field_confidence": payload.get("field_confidence", {}),
        }

    client = OCRClient()
    receipt_data = await client.extract_from_file(file_path)

    return {
        "amount": receipt_data.amount,
        "date": receipt_data.date,
        "vendor": receipt_data.vendor,
        "confidence": receipt_data.confidence,
        "extraction_method": "mock_filename",
        "source_hash": hashlib.sha256(file_path.encode("utf-8")).hexdigest(),
        "field_confidence": {
            "amount": receipt_data.confidence,
            "date": receipt_data.confidence,
            "vendor": receipt_data.confidence,
        },
    }


def score_transaction_match(receipt_data: dict, txn: dict) -> int:
    score = 0

    # Amount match (highest weight)
    if abs(txn.get("amount", 0) - receipt_data["amount"]) < 1:
        score += 50

    # Date proximity
    txn_date = txn.get("timestamp", "")
    if receipt_data["date"] in txn_date:
        score += 30

    # Vendor/VPA match
    if receipt_data["vendor"].lower() in str(txn.get("description", "")).lower():
        score += 20

    return score


async def match_transaction(
    receipt_data: dict,
    transactions: list,
    time_window_hours: int = 2,
) -> Optional[dict]:
    """
    Match receipt to existing transaction within time window.
    Returns best match or None.
    """
    best_match = None
    best_score = 0

    for txn in transactions:
        score = score_transaction_match(receipt_data, txn)

        if score > best_score and score >= 50:
            best_match = txn
            best_score = score

    return best_match


async def process_receipt_with_ocr(
    file_path: str,
    user_id: int,
    transactions: list,
) -> dict:
    """
    Full OCR processing: extract, match, and flag.
    """
    # Extract data
    extracted = await extract_receipt_data(file_path)

    # Try to match with transaction
    matched_txn = await match_transaction(extracted, transactions)
    match_score = score_transaction_match(extracted, matched_txn) if matched_txn else 0

    # Determine flag level
    if matched_txn:
        flag_level = "green"  # Verified match
    elif extracted["confidence"] > 0.8:
        flag_level = "yellow"  # Partial match
    else:
        flag_level = "red"  # No match
    needs_manual_review = (
        extracted["extraction_method"] == "mock_filename"
        or not matched_txn
        or match_score < 80
    )

    return {
        "extracted": extracted,
        "matched_transaction": matched_txn,
        "match_score": match_score,
        "matching_rule": "amount_date_vendor_weighted_v1",
        "flag_level": flag_level,
        "needs_manual_review": needs_manual_review,
    }
