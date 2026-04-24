import io
import re
import uuid

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

from config import ADMIN_IDS, DEFAULT_EMOJI, STORAGE_PATH
from image_utils import to_sticker_png
from storage import Storage

router = Router()
storage = Storage(STORAGE_PATH)

# Pending deletion confirmations: token -> pack name. Tokens are short so they
# fit the 64-byte callback_data limit alongside the pack name, which can be
# up to 64 bytes on its own.
_pending_deletes: dict[str, str] = {}


class DeletePackCB(CallbackData, prefix="delpack"):
    action: str  # "yes" | "no"
    token: str


class NewPack(StatesGroup):
    title = State()
    first_sticker = State()


# Reject anyone who isn't whitelisted. Runs first because it's the first
# handler registered; admins fall through to the real handlers below.
@router.message(~F.from_user.id.in_(ADMIN_IDS))
async def reject_non_admin(message: Message) -> None:
    await message.answer("Sorry, this bot is private.")


@router.callback_query(~F.from_user.id.in_(ADMIN_IDS))
async def reject_non_admin_cb(query: CallbackQuery) -> None:
    await query.answer("Not allowed.", show_alert=True)


@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Shared sticker-pack bot.\n\n"
        "<b>Commands</b>\n"
        "/newpack — create a new pack\n"
        "/setpack &lt;name&gt; — set active pack\n"
        "/listpacks — list known packs\n"
        "/current — show the active pack\n"
        "/removelast — remove the last sticker in the active pack\n"
        "/deletepack &lt;name&gt; — delete a pack on Telegram (asks to confirm)\n"
        "/forget &lt;name&gt; — stop tracking a pack locally (doesn't delete it on Telegram)\n"
        "/cancel — cancel the current operation\n\n"
        "<b>Adding stickers</b>\n"
        "Send a photo or an image file. Emoji in the caption will be attached; "
        f"otherwise {DEFAULT_EMOJI} is used. You can also forward an existing "
        "static sticker to copy it in."
    )


@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Nothing to cancel.")
        return
    await state.clear()
    await message.answer("Cancelled.")


@router.message(Command("current"))
async def cmd_current(message: Message, bot: Bot) -> None:
    active = storage.active()
    if not active:
        await message.answer("No active pack. Use /newpack or /setpack.")
        return
    try:
        set_ = await bot.get_sticker_set(active["name"])
        count = len(set_.stickers)
    except TelegramBadRequest:
        count = "?"
    await message.answer(
        f"Active pack: <b>{active['title']}</b>\n"
        f"Name: <code>{active['name']}</code>\n"
        f"Stickers: {count}\n"
        f"Link: https://t.me/addstickers/{active['name']}"
    )


@router.message(Command("listpacks"))
async def cmd_listpacks(message: Message) -> None:
    packs = storage.list_packs()
    if not packs:
        await message.answer("No packs yet. Use /newpack.")
        return
    active = storage.active()
    active_name = active["name"] if active else None
    lines = []
    for name, info in packs.items():
        marker = "➜ " if name == active_name else "   "
        lines.append(f"{marker}<b>{info['title']}</b> — <code>{name}</code>")
    await message.answer("\n".join(lines))


@router.message(Command("setpack"))
async def cmd_setpack(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: <code>/setpack &lt;name&gt;</code>")
        return
    name = parts[1].strip()
    try:
        storage.set_active(name)
    except KeyError:
        await message.answer(f"Unknown pack: <code>{name}</code>")
        return
    active = storage.active()
    await message.answer(f"Active pack is now <b>{active['title']}</b>.")


@router.message(Command("deletepack"))
async def cmd_deletepack(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: <code>/deletepack &lt;name&gt;</code>")
        return
    name = parts[1].strip()
    pack = storage.list_packs().get(name)
    if not pack:
        await message.answer(f"Unknown pack: <code>{name}</code>")
        return

    token = uuid.uuid4().hex[:8]
    _pending_deletes[token] = name
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Yes, delete",
                    callback_data=DeletePackCB(action="yes", token=token).pack(),
                ),
                InlineKeyboardButton(
                    text="✖ Cancel",
                    callback_data=DeletePackCB(action="no", token=token).pack(),
                ),
            ]
        ]
    )
    await message.answer(
        f"⚠️ Permanently delete <b>{pack['title']}</b> "
        f"(<code>{name}</code>) from Telegram? This cannot be undone.",
        reply_markup=kb,
    )


@router.callback_query(DeletePackCB.filter())
async def on_delete_pack_cb(
    query: CallbackQuery, callback_data: DeletePackCB, bot: Bot
) -> None:
    name = _pending_deletes.pop(callback_data.token, None)
    if name is None:
        await query.answer("Expired — run /deletepack again.", show_alert=True)
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        return

    if callback_data.action == "no":
        await query.message.edit_text(f"Cancelled — <code>{name}</code> kept.")
        await query.answer()
        return

    try:
        await bot.delete_sticker_set(name)
    except TelegramBadRequest as exc:
        await query.message.edit_text(
            f"Telegram rejected the delete: {exc.message}"
        )
        await query.answer()
        return

    storage.forget_pack(name)
    await query.message.edit_text(f"Deleted <code>{name}</code>.")
    await query.answer("Deleted")


@router.message(Command("forget"))
async def cmd_forget(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: <code>/forget &lt;name&gt;</code>")
        return
    name = parts[1].strip()
    if not storage.list_packs().get(name):
        await message.answer(f"Unknown pack: <code>{name}</code>")
        return
    storage.forget_pack(name)
    await message.answer(f"Forgotten <code>{name}</code>. The pack still exists on Telegram.")


@router.message(Command("newpack"))
async def cmd_newpack(message: Message, state: FSMContext) -> None:
    await state.set_state(NewPack.title)
    await message.answer(
        "Send a title for the new pack (max 64 chars). /cancel to abort."
    )


@router.message(NewPack.title, F.text)
async def newpack_title(message: Message, state: FSMContext, bot: Bot) -> None:
    title = (message.text or "").strip()
    if not (1 <= len(title) <= 64):
        await message.answer("Title must be 1–64 characters. Try again or /cancel.")
        return
    me = await bot.get_me()
    name = _make_pack_name(title, me.username)
    await state.update_data(title=title, name=name)
    await state.set_state(NewPack.first_sticker)
    await message.answer(
        f"Pack will be named <code>{name}</code>.\n"
        f"Now send the first image. Emoji in the caption become its tags; "
        f"otherwise {DEFAULT_EMOJI} is used."
    )


@router.message(NewPack.first_sticker, F.photo | F.document)
async def newpack_first_sticker(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    data = await state.get_data()
    title: str = data["title"]
    name: str = data["name"]

    sticker = await _build_sticker_from_image(message, bot)
    if sticker is None:
        await message.answer("That doesn't look like an image. Try again or /cancel.")
        return

    try:
        await bot.create_new_sticker_set(
            user_id=message.from_user.id,
            name=name,
            title=title,
            stickers=[sticker],
        )
    except TelegramBadRequest as exc:
        await message.answer(f"Telegram rejected the pack: {exc.message}")
        await state.clear()
        return

    storage.add_pack(name, title, message.from_user.id)
    await state.clear()
    await message.answer(
        f"Pack created!\nhttps://t.me/addstickers/{name}\n"
        f"Send more images to add to it."
    )


@router.message(F.photo | F.document)
async def add_sticker_from_image(message: Message, bot: Bot) -> None:
    active = storage.active()
    if not active:
        await message.answer("No active pack. Use /newpack or /setpack first.")
        return

    sticker = await _build_sticker_from_image(message, bot)
    if sticker is None:
        return  # non-image document, silently ignore

    try:
        await bot.add_sticker_to_set(
            user_id=active["owner_id"],
            name=active["name"],
            sticker=sticker,
        )
    except TelegramBadRequest as exc:
        await message.answer(f"Telegram rejected the sticker: {exc.message}")
        return

    try:
        total = len((await bot.get_sticker_set(active["name"])).stickers)
    except TelegramBadRequest:
        total = "?"
    await message.answer(f"Added to <b>{active['title']}</b> ({total} stickers).")


@router.message(F.sticker)
async def add_existing_sticker(message: Message, bot: Bot) -> None:
    active = storage.active()
    if not active:
        await message.answer("No active pack. Use /newpack or /setpack first.")
        return
    if message.sticker.is_animated or message.sticker.is_video:
        await message.answer("Animated/video stickers aren't supported here.")
        return

    sticker = InputSticker(
        sticker=message.sticker.file_id,
        format="static",
        emoji_list=[message.sticker.emoji or DEFAULT_EMOJI],
    )
    try:
        await bot.add_sticker_to_set(
            user_id=active["owner_id"],
            name=active["name"],
            sticker=sticker,
        )
    except TelegramBadRequest as exc:
        await message.answer(f"Telegram rejected the sticker: {exc.message}")
        return

    try:
        total = len((await bot.get_sticker_set(active["name"])).stickers)
    except TelegramBadRequest:
        total = "?"
    await message.answer(f"Added to <b>{active['title']}</b> ({total} stickers).")


@router.message(Command("removelast"))
async def cmd_removelast(message: Message, bot: Bot) -> None:
    active = storage.active()
    if not active:
        await message.answer("No active pack.")
        return
    try:
        set_ = await bot.get_sticker_set(active["name"])
    except TelegramBadRequest as exc:
        await message.answer(f"Pack lookup failed: {exc.message}")
        return
    if not set_.stickers:
        await message.answer("Pack is empty.")
        return
    last = set_.stickers[-1]
    try:
        await bot.delete_sticker_from_set(last.file_id)
    except TelegramBadRequest as exc:
        await message.answer(f"Couldn't remove: {exc.message}")
        return
    remaining = len(set_.stickers) - 1
    await message.answer(f"Removed. {remaining} stickers left.")


# ---------- helpers ----------

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


# Rough emoji ranges; good enough to pick out emoji from a caption.
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FFFF"
    "\U00002600-\U000027BF"
    "\U0001F300-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "]"
)


def _extract_emojis(text: str | None) -> list[str]:
    if not text:
        return []
    return _EMOJI_RE.findall(text)[:20]


async def _build_sticker_from_image(
    message: Message, bot: Bot
) -> InputSticker | None:
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document and (message.document.mime_type or "").startswith("image/"):
        file_id = message.document.file_id
    if not file_id:
        return None

    buf = io.BytesIO()
    await bot.download(file_id, destination=buf)
    png = to_sticker_png(buf.getvalue())

    emojis = _extract_emojis(message.caption) or [DEFAULT_EMOJI]
    return InputSticker(
        sticker=BufferedInputFile(png, filename="sticker.png"),
        format="static",
        emoji_list=emojis,
    )
