# tg-bot-stickers

A small private Telegram bot that lets **two whitelisted admins co-manage the same sticker pack** — shared write access without sharing a Telegram account.

## Why this exists

Telegram ties every sticker pack to a single user account: only that owner can use [@Stickers](https://t.me/Stickers) to add or remove stickers. That's inconvenient if two people want to build a pack together.

This bot works around it. When the first admin runs `/newpack`, the bot calls `createNewStickerSet` with their user id and stores that id as the pack's `owner_id` locally. Every later `addStickerToSet` / `deleteStickerFromSet` call uses that stored id, regardless of which admin triggered it. So both admins effectively write to the same pack through the bot.

## Setup

1. Create a bot via [@BotFather](https://t.me/BotFather) and grab the token.
2. Get the two admin numeric user ids via [@userinfobot](https://t.me/userinfobot).
3. Clone and configure:

   ```bash
   git clone <repo-url> tg-bot-stickers
   cd tg-bot-stickers
   cp .env.example .env
   # edit .env:
   #   BOT_TOKEN=...
   #   ADMIN_IDS=123456789,987654321
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

4. Run:

   ```bash
   .venv/bin/python bot.py
   ```

## Commands

| Command | What it does |
| --- | --- |
| `/start`, `/help` | Show help |
| `/newpack` | Create a new pack (FSM: title → first image) |
| `/setpack <name>` | Set the active pack |
| `/listpacks` | List known packs |
| `/current` | Show active pack + sticker count + link |
| `/removelast` | Remove the last sticker from the active pack |
| `/deletepack <name>` | Permanently delete a pack on Telegram (confirms with inline buttons) |
| `/forget <name>` | Drop a pack from local storage only; keeps it on Telegram |
| `/cancel` | Cancel the current operation |

Sending a photo or image file adds it to the active pack. Emoji in the caption become the sticker's tags; if none, 🎨 is used. Forwarding an existing static sticker copies it in by `file_id`.

Non-admins get a polite "this bot is private" reply; non-admin callback presses are silently rejected.

## Project layout

```
bot.py           # entry point
config.py        # loads BOT_TOKEN and ADMIN_IDS from .env
handlers.py      # all message + callback handlers, FSM
image_utils.py   # resize images so one side is exactly 512px (PNG)
storage.py       # JSON-backed pack metadata
```

State lives in `storage.json` next to the code — known packs, their owners, and the currently active pack. It's gitignored; delete it to start fresh.

## Image handling

Telegram requires static sticker images to have one side exactly 512px and the other ≤ 512px. `image_utils.to_sticker_png` resizes each upload to satisfy that while keeping aspect ratio, and re-encodes to PNG with an RGBA channel.

## Stack

- Python 3.12+
- [aiogram](https://github.com/aiogram/aiogram) 3.x — async Telegram bot framework
- Pillow — image resize
- python-dotenv — `.env` loading

## Security notes

- `.env` is gitignored. If you ever accidentally commit it, **rotate the token in @BotFather immediately** — a leaked token lets anyone take over the bot, including reading every message users send it.
- `storage.json` is also gitignored; it contains admin user ids and pack ownership info.
- The bot is locked to `ADMIN_IDS` — change those if your account changes.
