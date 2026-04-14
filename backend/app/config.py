# Database configuration
from pathlib import Path
import os

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# SQLite database path
DATABASE_PATH = Path(os.getenv("FLATWATCH_DATABASE_PATH", str(DATA_DIR / "flatwatch.db"))).expanduser()
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# API settings
API_TITLE = "FlatWatch API"
API_VERSION = "0.1.0"

# SSO Identity Provider
IDENTITY_URL = os.getenv("IDENTITY_URL", "https://aadharcha.in")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:43105")


def get_cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://localhost:43100",
        "http://127.0.0.1:43100",
        "http://localhost:43102",
        "http://127.0.0.1:43102",
        "http://localhost:43103",
        "http://127.0.0.1:43103",
        "http://localhost:43105",
        "http://127.0.0.1:43105",
    ]
