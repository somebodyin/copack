import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing in .env")

ADMIN_IDS = frozenset(
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip()
)
if not ADMIN_IDS:
    raise RuntimeError(
        "ADMIN_IDS missing in .env. Add the two admin telegram user ids, "
        "comma-separated, e.g. ADMIN_IDS=123456789,987654321. "
        "Ask @userinfobot for your numeric id."
    )


def _parse_admin_names(raw: str) -> dict[int, str]:
    """Parse `id1:Name,id2:Name` into {id: name}. Bad entries are skipped."""
    out: dict[int, str] = {}
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        sid, name = chunk.split(":", 1)
        try:
            out[int(sid.strip())] = name.strip()
        except ValueError:
            continue
    return out


# Optional per-id display names, used in /start greeting.
# Format: ADMIN_NAMES=123456789:Alice,987654321:Bob
ADMIN_NAMES: dict[int, str] = _parse_admin_names(os.getenv("ADMIN_NAMES", ""))

STORAGE_PATH = BASE_DIR / "storage.json"
DEFAULT_EMOJI = "🎨"
