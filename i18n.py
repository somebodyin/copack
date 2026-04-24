from storage import DEFAULT_LANG, storage

SUPPORTED = ("en", "uk")


def plural_uk(n: int, one: str, few: str, many: str) -> str:
    """Ukrainian plural form selector. Used for сtylized counts."""
    n = abs(int(n))
    n100 = n % 100
    if 11 <= n100 <= 14:
        return many
    n10 = n % 10
    if n10 == 1:
        return one
    if 2 <= n10 <= 4:
        return few
    return many


def stickers_word(n: int, lang: str) -> str:
    if lang == "uk":
        return plural_uk(n, "стікер", "стікери", "стікерів")
    return "sticker" if n == 1 else "stickers"


STRINGS: dict[str, dict[str, str]] = {
    "uk": {
        "private_only": "Цей бот приватний.",
        "not_allowed_cb": "Не дозволено.",

        "start": (
            "Привіт, {name}.\n\n"
            "Цей бот дозволяє двом адміністраторам спільно керувати стікерпаком. "
            "Надішліть фото або зображення, потім емоджі (або /skip) — і я додам стікер.\n\n"
            "/help — усі команди\n"
            "/lang — змінити мову"
        ),
        "help": (
            "<b>Команди</b>\n"
            "/newpack — створити новий пак\n"
            "/setpack &lt;name&gt; — обрати активний пак\n"
            "/listpacks — список паків\n"
            "/current — який пак зараз активний\n"
            "/removelast — прибрати останній стікер\n"
            "/deletepack &lt;name&gt; — повністю видалити пак (з підтвердженням)\n"
            "/forget &lt;name&gt; — забути пак локально (у Telegram лишиться)\n"
            "/lang &lt;uk|en&gt; — змінити мову\n"
            "/skip — у потоці додавання: пропустити емоджі, використати 🎨\n"
            "/cancel — скасувати дію\n\n"
            "<b>Як додавати стікери</b>\n"
            "Надсилайте фото або картинку файлом — я попрошу емоджі окремим "
            "повідомленням. Можна декілька; або /skip — і буде 🎨.\n"
            "Можна також пересилати готові статичні стікери — той самий потік."
        ),

        "nothing_to_cancel": "Нема що скасовувати.",
        "cancelled": "Скасовано.",

        "no_active_pack": "Активного паку немає. Використайте /newpack або /setpack.",
        "active_pack_info": (
            "Активний пак: <b>{title}</b>\n"
            "Назва: <code>{name}</code>\n"
            "Стікерів: {count} {sw}\n"
            "Посилання: {link}"
        ),

        "no_packs_yet": "Паків поки немає. Використайте /newpack.",
        "pack_list_marker_active": "-> ",
        "pack_list_marker_inactive": "   ",

        "set_pack_usage": "Використання: <code>/setpack &lt;name&gt;</code>",
        "unknown_pack": "Невідомий пак: <code>{name}</code>",
        "active_pack_set": "Активний пак — <b>{title}</b>.",

        "forget_usage": "Використання: <code>/forget &lt;name&gt;</code>",
        "forget_done": "Забуто <code>{name}</code>. Пак лишається у Telegram.",

        "delete_usage": "Використання: <code>/deletepack &lt;name&gt;</code>",
        "delete_confirm": (
            "⚠️ Назавжди видалити <b>{title}</b> (<code>{name}</code>) з Telegram?\n"
            "Скасувати буде неможливо."
        ),
        "delete_btn_yes": "✅ Так, видалити",
        "delete_btn_no": "✖ Скасувати",
        "delete_expired": "Прострочено — спробуйте /deletepack знову.",
        "delete_cancelled": "Скасовано — <code>{name}</code> залишається.",
        "delete_failed": "Telegram відхилив видалення: {error}",
        "delete_done": "Видалено <code>{name}</code>.",

        "newpack_title_prompt": (
            "Надішліть назву нового паку (до 64 символів).\n"
            "/cancel — щоб скасувати."
        ),
        "newpack_title_invalid": "Назва має бути від 1 до 64 символів. Спробуйте ще або /cancel.",
        "newpack_first_image_prompt": (
            "Пак буде <code>{name}</code>.\n"
            "Тепер надішліть перше зображення. Емоджі попрошу окремим повідомленням."
        ),

        "image_received_send_emoji": (
            "Зображення отримано.\n"
            "Тепер надішліть емоджі (одне або декілька) — стануть тегами стікера.\n"
            "Або /skip — використаю 🎨."
        ),
        "image_replaced_send_emoji": "Зображення замінено. Тепер емоджі або /skip.",
        "emoji_required": "Емоджі не знайдено. Спробуйте ще або /skip.",
        "send_image_or_sticker": "Надішліть фото, зображення файлом або стікер. /cancel — щоб скасувати.",
        "send_emoji_or_skip": "Надішліть емоджі або /skip (використаю 🎨). /cancel — щоб вийти.",

        "import_confirm": (
            "Додати стікер {emoji} до <b>{title}</b>?\n"
            "Джерело: <i>{source}</i>"
        ),
        "import_confirm_no_source": "Додати стікер {emoji} до <b>{title}</b>?",
        "import_btn_add": "✅ Додати",
        "import_btn_edit": "✏ Змінити емоджі",
        "import_btn_cancel": "✖ Скасувати",
        "import_cancelled": "Скасовано.",
        "import_expired": "Прострочено — перешліть стікер знову.",

        "not_an_image": "Не схоже на зображення. Спробуйте ще або /cancel.",
        "image_failed": "Не вдалося обробити: {error}",
        "telegram_rejected_pack": "Telegram відхилив пак: {error}",
        "pack_created": (
            "Пак створено.\n"
            "{link}\n"
            "Надсилайте ще фото — додам стікери."
        ),

        "telegram_rejected_sticker": "Telegram відхилив стікер: {error}",
        "sticker_added": "Додано до <b>{title}</b> ({count} {sw}).",
        "animated_not_supported": "Анімовані та відео-стікери не підтримуються.",

        "pack_lookup_failed": "Не вдалося знайти пак: {error}",
        "pack_empty": "Пак порожній.",
        "remove_failed": "Не вдалося видалити: {error}",
        "removed_remaining": "Видалено. Залишилось {count} {sw}.",

        "lang_usage": "Використання: <code>/lang uk</code> або <code>/lang en</code>",
        "lang_unsupported": "Підтримувані мови: en, uk",
        "lang_set": "Мову змінено на українську.",
    },

    "en": {
        "private_only": "Sorry, this bot is private.",
        "not_allowed_cb": "Not allowed.",

        "start": (
            "Hi, {name}.\n\n"
            "This bot lets two admins co-manage a sticker pack together. "
            "Send a photo or image, then emoji (or /skip), and I'll add a sticker.\n\n"
            "/help — all commands\n"
            "/lang — change language"
        ),
        "help": (
            "<b>Commands</b>\n"
            "/newpack — create a new pack\n"
            "/setpack &lt;name&gt; — set the active pack\n"
            "/listpacks — list packs\n"
            "/current — show the active pack\n"
            "/removelast — remove the last sticker\n"
            "/deletepack &lt;name&gt; — permanently delete a pack (asks to confirm)\n"
            "/forget &lt;name&gt; — drop a pack from local memory (stays on Telegram)\n"
            "/lang &lt;uk|en&gt; — change language\n"
            "/skip — while adding: skip the emoji prompt, use 🎨\n"
            "/cancel — cancel the current action\n\n"
            "<b>Adding stickers</b>\n"
            "Send a photo or an image file — I'll ask for the emoji in a separate "
            "message. Send one or more; or /skip and 🎨 is used.\n"
            "You can also forward existing static stickers — same flow."
        ),

        "nothing_to_cancel": "Nothing to cancel.",
        "cancelled": "Cancelled.",

        "no_active_pack": "No active pack. Use /newpack or /setpack.",
        "active_pack_info": (
            "Active pack: <b>{title}</b>\n"
            "Name: <code>{name}</code>\n"
            "Stickers: {count} {sw}\n"
            "Link: {link}"
        ),

        "no_packs_yet": "No packs yet. Use /newpack.",
        "pack_list_marker_active": "-> ",
        "pack_list_marker_inactive": "   ",

        "set_pack_usage": "Usage: <code>/setpack &lt;name&gt;</code>",
        "unknown_pack": "Unknown pack: <code>{name}</code>",
        "active_pack_set": "Active pack is now <b>{title}</b>.",

        "forget_usage": "Usage: <code>/forget &lt;name&gt;</code>",
        "forget_done": "Forgotten <code>{name}</code>. The pack still exists on Telegram.",

        "delete_usage": "Usage: <code>/deletepack &lt;name&gt;</code>",
        "delete_confirm": (
            "⚠️ Permanently delete <b>{title}</b> (<code>{name}</code>) from Telegram?\n"
            "This cannot be undone."
        ),
        "delete_btn_yes": "✅ Yes, delete",
        "delete_btn_no": "✖ Cancel",
        "delete_expired": "Expired — run /deletepack again.",
        "delete_cancelled": "Cancelled — <code>{name}</code> kept.",
        "delete_failed": "Telegram rejected the delete: {error}",
        "delete_done": "Deleted <code>{name}</code>.",

        "newpack_title_prompt": (
            "Send a title for the new pack (max 64 chars). /cancel to abort."
        ),
        "newpack_title_invalid": "Title must be 1–64 characters. Try again or /cancel.",
        "newpack_first_image_prompt": (
            "Pack will be named <code>{name}</code>.\n"
            "Now send the first image. I'll ask for the emoji separately."
        ),

        "image_received_send_emoji": (
            "Image received.\n"
            "Now send the emoji (one or more) — they'll become the sticker's tags.\n"
            "Or /skip to use 🎨."
        ),
        "image_replaced_send_emoji": "Image replaced. Now send emoji or /skip.",
        "emoji_required": "No emoji found. Try again or /skip.",
        "send_image_or_sticker": "Send a photo, image file, or sticker. /cancel to abort.",
        "send_emoji_or_skip": "Send emoji, or /skip to use 🎨. /cancel to abort.",

        "import_confirm": (
            "Add this sticker {emoji} to <b>{title}</b>?\n"
            "Source: <i>{source}</i>"
        ),
        "import_confirm_no_source": "Add this sticker {emoji} to <b>{title}</b>?",
        "import_btn_add": "✅ Add",
        "import_btn_edit": "✏ Change emoji",
        "import_btn_cancel": "✖ Cancel",
        "import_cancelled": "Cancelled.",
        "import_expired": "Expired — forward the sticker again.",

        "not_an_image": "Not a recognised image. Try again or /cancel.",
        "image_failed": "Image processing failed: {error}",
        "telegram_rejected_pack": "Telegram rejected the pack: {error}",
        "pack_created": (
            "Pack created.\n"
            "{link}\n"
            "Send more photos to add stickers."
        ),

        "telegram_rejected_sticker": "Telegram rejected the sticker: {error}",
        "sticker_added": "Added to <b>{title}</b> ({count} {sw}).",
        "animated_not_supported": "Animated and video stickers are not supported.",

        "pack_lookup_failed": "Pack lookup failed: {error}",
        "pack_empty": "Pack is empty.",
        "remove_failed": "Couldn't remove: {error}",
        "removed_remaining": "Removed. {count} {sw} left.",

        "lang_usage": "Usage: <code>/lang uk</code> or <code>/lang en</code>",
        "lang_unsupported": "Supported languages: en, uk",
        "lang_set": "Language set to English.",
    },
}


def t(key: str, **fmt) -> str:
    lang = storage.get_lang()
    bundle = STRINGS.get(lang, STRINGS[DEFAULT_LANG])
    text = bundle.get(key) or STRINGS[DEFAULT_LANG].get(key) or key
    return text.format(**fmt) if fmt else text
