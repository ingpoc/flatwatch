# FlatWatch FastAPI Application
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import API_TITLE, API_VERSION, get_cors_origins
from .database import init_db, get_db_connection
from .models import HealthResponse
from .routers import auth, admin, transactions, receipts, ocr, chat, challenges, audit, scanner, notifications, control_plane


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    init_db()
    yield
    # Shutdown (if needed)


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(transactions.router)
app.include_router(receipts.router)
app.include_router(ocr.router)
app.include_router(chat.router)
app.include_router(challenges.router)
app.include_router(audit.router)
app.include_router(scanner.router)
app.include_router(notifications.router)
app.include_router(control_plane.router)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT COUNT(*) as count FROM transactions")
        result = cursor.fetchone()
        conn.close()

        return HealthResponse(
            status="healthy",
            database=f"connected ({result['count']} transactions)",
            version=API_VERSION,
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            database=f"error: {str(e)}",
            version=API_VERSION,
        )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "FlatWatch API",
        "version": API_VERSION,
        "docs": "/api/docs",
        "auth": "/api/auth",
    }
