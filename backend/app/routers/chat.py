# Chat router for FlatWatch
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..rbac import require_resident
from ..auth import User
from ..chat import process_chat_query, query_transactions


class ChatRequest(BaseModel):
    query: str
    session_id: str = None


class ChatResponse(BaseModel):
    query: str
    response: str
    session_id: str
    timestamp: str


router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    current_user: User = Depends(require_resident),
):
    """
    Process natural language query about finances.
    """
    result = await process_chat_query(
        request.query,
        current_user.id,
        request.session_id,
    )
    return result


@router.post("/query-transactions")
async def query_transactions_endpoint(
    request: ChatRequest,
    current_user: User = Depends(require_resident),
):
    """
    Query transactions using natural language.
    Returns matching transactions.
    """
    transactions = await query_transactions(request.query)

    return {
        "query": request.query,
        "transactions": transactions,
        "count": len(transactions),
    }
