import os
from pathlib import Path


# Keep pytest runs off the live dev database so local browser/runtime flows remain intact.
os.environ.setdefault(
    "FLATWATCH_DATABASE_PATH",
    str((Path(__file__).parent / ".tmp" / "flatwatch-test.db").resolve()),
)
