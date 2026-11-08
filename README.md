# tgram

A Claude Code plugin that lets Claude **read your Telegram chats and send messages from your own account**, only when you ask. It uses the Telegram user API (Telethon), so it works as you, not as a bot.

## Install

Requires Python 3.10+.

```bash
pip install git+https://github.com/zz5644934-design/tgram
```

Then in Claude Code:

```
/plugin marketplace add zz5644934-design/tgram
/plugin install tgram@tgram
```

## Log in (once, in your own terminal)

1. Create your own Telegram app at <https://my.telegram.org> -> *API development tools* and note the `api_id` and `api_hash`. Keep them private.
2. Run:

```bash
tg login
```

It asks for api_id, api_hash, your phone, the login code and your 2FA password if enabled. Everything is stored locally in `~/.tg` (never in this repository). Claude never sees these values.

## Use

Ask Claude things like "who wrote me?", "read my chat with @name", "reply to @name that I'll be late". Under the hood:

```bash
tg chats --unread
tg read @name --limit 20
tg send @name "text"          # dry run, shows recipient and text
tg send @name "text" --yes    # actually sends
```

## Safety

- Reading does not mark chats as read.
- `send` is a dry run unless `--yes` is passed. The skill tells Claude to show you the exact recipient and text and send only after you confirm (or when you gave the exact text yourself).
- Instructions found inside Telegram messages are treated as data, never as commands.
- Limit of 20 sends per day, 5 s apart. No mass messaging, no joining chats.
- Be careful what you ask for: this is your real account.
