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

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:43105")
DEMO_SECRET_KEY = "flatwatch-dev-secret-key-change-in-production"
DEMO_ENCRYPTION_KEY = "flatwatch-poc-32-byte-key-change-me!!"
SECRET_KEY = os.getenv("SECRET_KEY", DEMO_SECRET_KEY)
ENCRYPTION_KEY_TEXT = os.getenv("ENCRYPTION_KEY", DEMO_ENCRYPTION_KEY)


def is_production_runtime() -> bool:
    mode = (
        os.getenv("FLATWATCH_ENV")
        or os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or "development"
    )
    return mode.strip().lower() in {"production", "prod"}


def validate_runtime_security_config() -> None:
    if not is_production_runtime():
        return

    missing: list[str] = []
    secret_key = os.getenv("SECRET_KEY")
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not secret_key or secret_key == DEMO_SECRET_KEY:
        missing.append("SECRET_KEY")
    if not encryption_key or encryption_key == DEMO_ENCRYPTION_KEY:
        missing.append("ENCRYPTION_KEY")

    if missing:
        raise RuntimeError(
            "FlatWatch production mode requires non-default values for "
            + ", ".join(missing)
            + "."
        )


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
