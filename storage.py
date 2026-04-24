import json
from pathlib import Path
from typing import Optional

from config import STORAGE_PATH

DEFAULT_LANG = "en"


class Storage:
    """Tiny JSON-backed store for pack metadata.

    Each pack records its owner_id — the user whose id was used to create
    the sticker set. Telegram ties a set to that one owner, so every
    subsequent addStickerToSet call must use that same id, regardless of
    which admin uploaded the image.
    """

    def __init__(self, path: Path):
        self.path = path
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            data.setdefault("lang", DEFAULT_LANG)
            return data
        return {"packs": {}, "active_pack": None, "lang": DEFAULT_LANG}

    def _save(self) -> None:
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_pack(self, name: str, title: str, owner_id: int) -> None:
        self._data["packs"][name] = {"title": title, "owner_id": owner_id}
        self._data["active_pack"] = name
        self._save()

    def set_active(self, name: str) -> None:
        if name not in self._data["packs"]:
            raise KeyError(name)
        self._data["active_pack"] = name
        self._save()

    def active(self) -> Optional[dict]:
        name = self._data.get("active_pack")
        if not name:
            return None
        pack = self._data["packs"].get(name)
        if not pack:
            return None
        return {"name": name, **pack}

    def list_packs(self) -> dict:
        return dict(self._data["packs"])

    def forget_pack(self, name: str) -> None:
        self._data["packs"].pop(name, None)
        if self._data.get("active_pack") == name:
            self._data["active_pack"] = None
        self._save()

    def get_lang(self) -> str:
        return self._data.get("lang", DEFAULT_LANG)

    def set_lang(self, lang: str) -> None:
        self._data["lang"] = lang
        self._save()


# Module-level singleton — imported by handlers and i18n.
storage = Storage(STORAGE_PATH)
