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

STORAGE_PATH = BASE_DIR / "storage.json"
DEFAULT_EMOJI = "🎨"
