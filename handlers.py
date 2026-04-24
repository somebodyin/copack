import io
import logging
import re
import uuid

import emoji as emoji_lib
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputSticker,
    Message,
)

from config import ADMIN_IDS, ADMIN_NAMES, DEFAULT_EMOJI
from i18n import SUPPORTED, stickers_word, t
from image_utils import to_sticker_png
from storage import storage

router = Router()
log = logging.getLogger(__name__)

# Pending deletion confirmations: token -> pack name. Tokens are short so they
# fit the 64-byte callback_data limit alongside the pack name, which can be
# up to 64 bytes on its own.
_pending_deletes: dict[str, str] = {}


class DeletePackCB(CallbackData, prefix="delpack"):
    action: str  # "yes" | "no"
    token: str


class ImportStickerCB(CallbackData, prefix="impstk"):
    action: str  # "add" | "edit" | "cancel"
    token: str


# Pending sticker imports awaiting user confirmation.
_pending_imports: dict[str, dict] = {}


class NewPack(StatesGroup):
    title = State()
    first_image = State()
    first_emoji = State()


class AddSticker(StatesGroup):
    waiting_emoji = State()


# Reject anyone who isn't whitelisted. Runs first because it's the first
# handler registered; admins fall through to the real handlers below.
@router.message(~F.from_user.id.in_(ADMIN_IDS))
async def reject_non_admin(message: Message) -> None:
    await message.answer(t("private_only"))


@router.callback_query(~F.from_user.id.in_(ADMIN_IDS))
async def reject_non_admin_cb(query: CallbackQuery) -> None:
    await query.answer(t("not_allowed_cb"), show_alert=True)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(t("start", name=_display_name(message)))


def _display_name(message: Message) -> str:
    user = message.from_user
    return ADMIN_NAMES.get(user.id) or (user.first_name or "").strip() or "there"


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(t("help"))


@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer(t("nothing_to_cancel"))
        return
    await state.clear()
    await message.answer(t("cancelled"))


@router.message(Command("lang"))
async def cmd_lang(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("lang_usage"))
        return
    lang = parts[1].strip().lower()
    if lang not in SUPPORTED:
        await message.answer(t("lang_unsupported"))
        return
    storage.set_lang(lang)
    await message.answer(t("lang_set"))  # rendered in the new language


@router.message(Command("current"))
async def cmd_current(message: Message, bot: Bot) -> None:
    active = storage.active()
    if not active:
        await message.answer(t("no_active_pack"))
        return
    try:
        set_ = await bot.get_sticker_set(active["name"])
        count = len(set_.stickers)
    except TelegramBadRequest:
        count = 0
    await message.answer(
        t(
            "active_pack_info",
            title=active["title"],
            name=active["name"],
            count=count,
            sw=stickers_word(count, storage.get_lang()),
            link=f"https://t.me/addstickers/{active['name']}",
        )
    )


@router.message(Command("listpacks"))
async def cmd_listpacks(message: Message) -> None:
    packs = storage.list_packs()
    if not packs:
        await message.answer(t("no_packs_yet"))
        return
    active = storage.active()
    active_name = active["name"] if active else None
    lines = []
    for name, info in packs.items():
        marker = (
            t("pack_list_marker_active")
            if name == active_name
            else t("pack_list_marker_inactive")
        )
        lines.append(f"{marker}<b>{info['title']}</b> — <code>{name}</code>")
    await message.answer("\n".join(lines))


@router.message(Command("setpack"))
async def cmd_setpack(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("set_pack_usage"))
        return
    name = parts[1].strip()
    try:
        storage.set_active(name)
    except KeyError:
        await message.answer(t("unknown_pack", name=name))
        return
    active = storage.active()
    await message.answer(t("active_pack_set", title=active["title"]))


@router.message(Command("deletepack"))
async def cmd_deletepack(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("delete_usage"))
        return
    name = parts[1].strip()
    pack = storage.list_packs().get(name)
    if not pack:
        await message.answer(t("unknown_pack", name=name))
        return

    token = uuid.uuid4().hex[:8]
    _pending_deletes[token] = name
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("delete_btn_yes"),
                    callback_data=DeletePackCB(action="yes", token=token).pack(),
                ),
                InlineKeyboardButton(
                    text=t("delete_btn_no"),
                    callback_data=DeletePackCB(action="no", token=token).pack(),
                ),
            ]
        ]
    )
    await message.answer(
        t("delete_confirm", title=pack["title"], name=name),
        reply_markup=kb,
    )


@router.callback_query(DeletePackCB.filter())
async def on_delete_pack_cb(
    query: CallbackQuery, callback_data: DeletePackCB, bot: Bot
) -> None:
    name = _pending_deletes.pop(callback_data.token, None)
    if name is None:
        await query.answer(t("delete_expired"), show_alert=True)
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        return

    if callback_data.action == "no":
        await query.message.edit_text(t("delete_cancelled", name=name))
        await query.answer()
        return

    try:
        await bot.delete_sticker_set(name)
    except TelegramBadRequest as exc:
        await query.message.edit_text(t("delete_failed", error=exc.message))
        await query.answer()
        return

    storage.forget_pack(name)
    await query.message.edit_text(t("delete_done", name=name))
    await query.answer()


@router.message(Command("forget"))
async def cmd_forget(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(t("forget_usage"))
        return
    name = parts[1].strip()
    if not storage.list_packs().get(name):
        await message.answer(t("unknown_pack", name=name))
        return
    storage.forget_pack(name)
    await message.answer(t("forget_done", name=name))


@router.message(Command("removelast"))
async def cmd_removelast(message: Message, bot: Bot) -> None:
    active = storage.active()
    if not active:
        await message.answer(t("no_active_pack"))
        return
    try:
        set_ = await bot.get_sticker_set(active["name"])
    except TelegramBadRequest as exc:
        await message.answer(t("pack_lookup_failed", error=exc.message))
        return
    if not set_.stickers:
        await message.answer(t("pack_empty"))
        return
    last = set_.stickers[-1]
    try:
        await bot.delete_sticker_from_set(last.file_id)
    except TelegramBadRequest as exc:
        await message.answer(t("remove_failed", error=exc.message))
        return
    remaining = len(set_.stickers) - 1
    await message.answer(
        t(
            "removed_remaining",
            count=remaining,
            sw=stickers_word(remaining, storage.get_lang()),
        )
    )


@router.message(Command("newpack"))
async def cmd_newpack(message: Message, state: FSMContext) -> None:
    await state.set_state(NewPack.title)
    await message.answer(t("newpack_title_prompt"))


@router.message(NewPack.title, F.text)
async def newpack_title(message: Message, state: FSMContext, bot: Bot) -> None:
    title = (message.text or "").strip()
    if not (1 <= len(title) <= 64):
        await message.answer(t("newpack_title_invalid"))
        return
    me = await bot.get_me()
    name = _make_pack_name(title, me.username)
    await state.update_data(title=title, name=name)
    await state.set_state(NewPack.first_image)
    await message.answer(t("newpack_first_image_prompt", name=name))


# ---- /newpack: receiving the first image (or sticker), then emoji ----

@router.message(NewPack.first_image, F.photo | F.document)
async def newpack_first_image(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    if not await _store_image_in_state(message, state, bot):
        await message.answer(t("not_an_image"))
        return
    await state.set_state(NewPack.first_emoji)
    await message.answer(t("image_received_send_emoji"))


@router.message(NewPack.first_image, F.sticker)
async def newpack_first_sticker_input(
    message: Message, state: FSMContext
) -> None:
    if not await _store_sticker_in_state(message, state):
        return
    await state.set_state(NewPack.first_emoji)
    await message.answer(t("image_received_send_emoji"))


@router.message(NewPack.first_emoji, F.photo | F.document)
async def newpack_first_image_replace(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    if not await _store_image_in_state(message, state, bot):
        return
    await message.answer(t("image_replaced_send_emoji"))


@router.message(NewPack.first_emoji, F.sticker)
async def newpack_first_sticker_replace(
    message: Message, state: FSMContext
) -> None:
    if not await _store_sticker_in_state(message, state):
        return
    await message.answer(t("image_replaced_send_emoji"))


@router.message(NewPack.first_emoji, Command("skip"))
async def newpack_first_skip(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    data = await state.get_data()
    fallback = data.get("suggested_emoji") or DEFAULT_EMOJI
    await _create_pack(message, state, bot, [fallback])


@router.message(NewPack.first_emoji, F.text)
async def newpack_first_emoji(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    emojis = _extract_emojis(message.text)
    if not emojis:
        await message.answer(t("emoji_required"))
        return
    await _create_pack(message, state, bot, emojis)


# ---- adding to existing pack: image/sticker first, then emoji ----

@router.message(StateFilter(None), F.photo | F.document)
async def add_image_start(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    active = storage.active()
    if not active:
        await message.answer(t("no_active_pack"))
        return
    if not await _store_image_in_state(message, state, bot):
        return
    await state.set_state(AddSticker.waiting_emoji)
    await message.answer(t("image_received_send_emoji"))


@router.message(StateFilter(None), F.sticker)
async def import_sticker_confirm(
    message: Message, bot: Bot
) -> None:
    active = storage.active()
    if not active:
        await message.answer(t("no_active_pack"))
        return
    st = message.sticker
    if st.is_animated or st.is_video:
        await message.answer(t("animated_not_supported"))
        return

    suggested = st.emoji or DEFAULT_EMOJI
    source_title = await _sticker_set_title(bot, st.set_name)

    token = uuid.uuid4().hex[:8]
    _pending_imports[token] = {
        "file_id": st.file_id,
        "emoji": suggested,
    }

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("import_btn_add"),
                    callback_data=ImportStickerCB(action="add", token=token).pack(),
                ),
                InlineKeyboardButton(
                    text=t("import_btn_edit"),
                    callback_data=ImportStickerCB(action="edit", token=token).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("import_btn_cancel"),
                    callback_data=ImportStickerCB(action="cancel", token=token).pack(),
                ),
            ],
        ]
    )
    key = "import_confirm" if source_title else "import_confirm_no_source"
    await message.answer(
        t(key, emoji=suggested, title=active["title"], source=source_title or ""),
        reply_markup=kb,
    )


@router.callback_query(ImportStickerCB.filter())
async def on_import_sticker_cb(
    query: CallbackQuery,
    callback_data: ImportStickerCB,
    bot: Bot,
    state: FSMContext,
) -> None:
    pending = _pending_imports.pop(callback_data.token, None)
    if pending is None:
        await query.answer(t("import_expired"), show_alert=True)
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        return

    if callback_data.action == "cancel":
        await query.message.edit_text(t("import_cancelled"))
        await query.answer()
        return

    if callback_data.action == "edit":
        await state.update_data(
            source="sticker",
            file_id=pending["file_id"],
            suggested_emoji=pending["emoji"],
            png=None,
        )
        await state.set_state(AddSticker.waiting_emoji)
        await query.message.edit_text(t("image_received_send_emoji"))
        await query.answer()
        return

    # action == "add"
    active = storage.active()
    if not active:
        await query.message.edit_text(t("no_active_pack"))
        await query.answer()
        return

    sticker = InputSticker(
        sticker=pending["file_id"],
        format="static",
        emoji_list=[pending["emoji"] or DEFAULT_EMOJI],
    )
    try:
        await bot.add_sticker_to_set(
            user_id=active["owner_id"],
            name=active["name"],
            sticker=sticker,
        )
    except TelegramBadRequest as exc:
        await query.message.edit_text(
            t("telegram_rejected_sticker", error=exc.message)
        )
        await query.answer()
        return

    try:
        total = len((await bot.get_sticker_set(active["name"])).stickers)
    except TelegramBadRequest:
        total = 0
    await query.message.edit_text(
        t(
            "sticker_added",
            title=active["title"],
            count=total,
            sw=stickers_word(total, storage.get_lang()),
        )
    )
    await query.answer()


async def _sticker_set_title(bot: Bot, set_name: str | None) -> str | None:
    if not set_name:
        return None
    try:
        st_set = await bot.get_sticker_set(set_name)
        return st_set.title
    except TelegramBadRequest:
        return set_name


@router.message(AddSticker.waiting_emoji, F.photo | F.document)
async def add_replace_image(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    if not await _store_image_in_state(message, state, bot):
        return
    await message.answer(t("image_replaced_send_emoji"))


@router.message(AddSticker.waiting_emoji, F.sticker)
async def add_replace_sticker(
    message: Message, state: FSMContext
) -> None:
    if not await _store_sticker_in_state(message, state):
        return
    await message.answer(t("image_replaced_send_emoji"))


@router.message(AddSticker.waiting_emoji, Command("skip"))
async def add_skip(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    data = await state.get_data()
    fallback = data.get("suggested_emoji") or DEFAULT_EMOJI
    await _finalize_add(message, state, bot, [fallback])


@router.message(AddSticker.waiting_emoji, F.text)
async def add_emoji(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    emojis = _extract_emojis(message.text)
    if not emojis:
        await message.answer(t("emoji_required"))
        return
    await _finalize_add(message, state, bot, emojis)


# Catch-alls for active FSM states. Registered *after* every state-specific
# handler so they only fire on truly unhandled inputs (audio, video_note,
# location, contact, etc.). Without these, unsupported types vanish silently.

@router.message(NewPack.first_image)
async def newpack_first_image_other(message: Message) -> None:
    await message.answer(t("send_image_or_sticker"))


@router.message(NewPack.first_emoji)
async def newpack_first_emoji_other(message: Message) -> None:
    await message.answer(t("send_emoji_or_skip"))


@router.message(AddSticker.waiting_emoji)
async def add_waiting_emoji_other(message: Message) -> None:
    await message.answer(t("send_emoji_or_skip"))


# ---------- helpers ----------

async def _announce_added(message: Message, bot: Bot, active: dict) -> None:
    try:
        total = len((await bot.get_sticker_set(active["name"])).stickers)
    except TelegramBadRequest:
        total = 0
    await message.answer(
        t(
            "sticker_added",
            title=active["title"],
            count=total,
            sw=stickers_word(total, storage.get_lang()),
        )
    )


# Telegram pack names: letters/digits/underscores, start with a letter,
# no consecutive underscores, must end with `_by_<bot_username>`, total <= 64.
def _make_pack_name(title: str, bot_username: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_").lower()
    slug = re.sub(r"_+", "_", slug)
    if not slug or not slug[0].isalpha():
        slug = f"p_{slug}".strip("_")
    suffix = f"_by_{bot_username}"
    budget = 64 - len(suffix)
    slug = slug[:budget].rstrip("_") or "pack"
    return f"{slug}{suffix}"


def _extract_emojis(text: str | None) -> list[str]:
    """Pull distinct emoji out of text, respecting ZWJ sequences.

    Returns unique emoji in order of first appearance, capped at 20 (Telegram's
    per-sticker limit). Uses `emoji.emoji_list` (position-ordered) + manual
    dedupe because `distinct_emoji_list` is set-backed and its order is not
    stable across runs. ZWJ-joined glyphs like 👩‍❤️‍💋‍👨 count as one emoji.
    """
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in emoji_lib.emoji_list(text):
        ch = item["emoji"]
        if ch not in seen:
            seen.add(ch)
            out.append(ch)
    return out[:20]


async def _store_image_in_state(
    message: Message, state: FSMContext, bot: Bot
) -> bool:
    """Download + normalise the image, store it in FSM state, return True on success.

    Returns False (and does not write to state) if the message has no usable
    image. Surfaces processing errors to the user via t("image_failed", ...).
    """
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document and (message.document.mime_type or "").startswith("image/"):
        file_id = message.document.file_id
    if not file_id:
        return False
    try:
        buf = io.BytesIO()
        await bot.download(file_id, destination=buf)
        png = to_sticker_png(buf.getvalue())
    except Exception as exc:  # noqa: BLE001 — we want to surface anything PIL throws
        log.exception("image processing failed")
        await message.answer(t("image_failed", error=str(exc)))
        return False
    await state.update_data(
        source="image", png=png, file_id=None, suggested_emoji=None
    )
    return True


async def _store_sticker_in_state(
    message: Message, state: FSMContext
) -> bool:
    """Stash a forwarded/sent sticker's file_id in FSM state for later use."""
    if message.sticker.is_animated or message.sticker.is_video:
        await message.answer(t("animated_not_supported"))
        return False
    await state.update_data(
        source="sticker",
        file_id=message.sticker.file_id,
        suggested_emoji=message.sticker.emoji,
        png=None,
    )
    return True


def _build_input_sticker(data: dict, emojis: list[str]) -> InputSticker:
    if data.get("source") == "sticker":
        return InputSticker(
            sticker=data["file_id"],
            format="static",
            emoji_list=emojis,
        )
    return InputSticker(
        sticker=BufferedInputFile(data["png"], filename="sticker.png"),
        format="static",
        emoji_list=emojis,
    )


async def _create_pack(
    message: Message, state: FSMContext, bot: Bot, emojis: list[str]
) -> None:
    data = await state.get_data()
    sticker = _build_input_sticker(data, emojis)
    try:
        await bot.create_new_sticker_set(
            user_id=message.from_user.id,
            name=data["name"],
            title=data["title"],
            stickers=[sticker],
        )
    except TelegramBadRequest as exc:
        await message.answer(t("telegram_rejected_pack", error=exc.message))
        await state.clear()
        return

    storage.add_pack(data["name"], data["title"], message.from_user.id)
    await state.clear()
    await message.answer(
        t("pack_created", link=f"https://t.me/addstickers/{data['name']}")
    )


async def _finalize_add(
    message: Message, state: FSMContext, bot: Bot, emojis: list[str]
) -> None:
    active = storage.active()
    if not active:
        await message.answer(t("no_active_pack"))
        await state.clear()
        return
    data = await state.get_data()
    sticker = _build_input_sticker(data, emojis)
    try:
        await bot.add_sticker_to_set(
            user_id=active["owner_id"],
            name=active["name"],
            sticker=sticker,
        )
    except TelegramBadRequest as exc:
        await message.answer(t("telegram_rejected_sticker", error=exc.message))
        await state.clear()
        return
    await state.clear()
    await _announce_added(message, bot, active)
