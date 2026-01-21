# Chat Guard - Mock AI agent for FlatWatch (POC)
from typing import List, Optional
from datetime import datetime, timedelta


class ChatMessage:
    """Chat message."""
    def __init__(self, role: str, content: str):
        self.role = role  # 'user' or 'assistant'
        self.content = content


class ChatSession:
    """Chat session with context."""

    def __init__(self):
        self.messages: List[ChatMessage] = []
        self.created_at = datetime.now()

    def add_message(self, role: str, content: str):
        """Add message to session."""
        self.messages.append(ChatMessage(role, content))

    def get_context(self) -> str:
        """Get conversation context."""
        return "\n".join([f"{m.role}: {m.content}" for m in self.messages])


# Mock chat responses (POC)
CHAT_RESPONSES = {
    "balance": "The current balance is ₹125,000. Total inflow: ₹600,000, outflow: ₹475,000.",
    "transactions": "I can help you query transactions. Try asking 'show water bills' or 'recent expenses'.",
    "water bill": "Water bills this month: ₹8,500 paid on Jan 20. Status: Verified.",
    "maintenance": "Maintenance collections: ₹12,000 collected (2 flats × ₹6,000). Status: All verified.",
    "unmatched": "There are 3 unmatched transactions requiring review.",
    "help": "I can help you with:\n- Balance inquiries\n- Transaction searches\n- Verification status\n- Compliance questions",
}


async def process_chat_query(
    query: str,
    user_id: int,
    session_id: Optional[str] = None,
) -> dict:
    """
    Process user chat query (POC mock).
    In production, this will use Claude Agent SDK.
    """
    query_lower = query.lower()

    # Find relevant response
    response = "I'm not sure about that. Try asking about balance, transactions, or unmatched entries."

    for keyword, answer in CHAT_RESPONSES.items():
        if keyword in query_lower:
            response = answer
            break

    # For specific questions about amounts
    if "how much" in query_lower or "what is" in query_lower:
        if "balance" in query_lower:
            response = CHAT_RESPONSES["balance"]
        elif "unmatched" in query_lower:
            response = CHAT_RESPONSES["unmatched"]

    return {
        "query": query,
        "response": response,
        "session_id": session_id or "mock_session_123",
        "timestamp": datetime.now().isoformat(),
    }


async def query_transactions(
    query: str,
    filters: dict = None,
) -> List[dict]:
    """
    Query transactions based on natural language.
    """
    from .database import get_db_connection

    conn = get_db_connection()
    query_sql = "SELECT * FROM transactions WHERE 1=1"
    params = []

    # Parse query for filters
    query_lower = query.lower()

    # Type filter
    if "inflow" in query_lower or "income" in query_lower:
        query_sql += " AND transaction_type = 'inflow'"
    elif "outflow" in query_lower or "expense" in query_lower or "payment" in query_lower:
        query_sql += " AND transaction_type = 'outflow'"

    # Amount filter
    if "last" in query_lower or "recent" in query_lower:
        query_sql += " AND datetime(timestamp) > datetime('now', '-7 days')"

    query_sql += " ORDER BY timestamp DESC LIMIT 10"

    cursor = conn.execute(query_sql, params)
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return transactions
