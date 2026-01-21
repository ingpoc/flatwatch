# OCR integration for FlatWatch (POC mock)
from datetime import datetime
from typing import Optional
import re


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
    client = OCRClient()
    receipt_data = await client.extract_from_file(file_path)

    return {
        "amount": receipt_data.amount,
        "date": receipt_data.date,
        "vendor": receipt_data.vendor,
        "confidence": receipt_data.confidence,
    }


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

    # Determine flag level
    if matched_txn:
        flag_level = "green"  # Verified match
    elif extracted["confidence"] > 0.8:
        flag_level = "yellow"  # Partial match
    else:
        flag_level = "red"  # No match

    return {
        "extracted": extracted,
        "matched_transaction": matched_txn,
        "flag_level": flag_level,
    }
