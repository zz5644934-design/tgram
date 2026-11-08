"""tg - Telegram CLI (MTProto via Telethon). Session stored in ~/.tg. Reading never marks chats as read."""
import argparse, asyncio, getpass, json, sys, time
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

HOME = Path.home() / ".tg"
CFG = HOME / "config.json"
SESSION = str(HOME / "session")
SENDS = HOME / "sends.json"
SEND_DAILY_CAP = 20
SEND_MIN_INTERVAL = 5
EXIT_NEED_LOGIN = 3


def cfg():
    try:
        return json.loads(CFG.read_text("utf-8"))
    except Exception:
        return None


def client():
    c = cfg()
    if not c:
        print("NEED_LOGIN: run `tg login` in your own terminal", file=sys.stderr)
        sys.exit(EXIT_NEED_LOGIN)
    return TelegramClient(SESSION, int(c["api_id"]), c["api_hash"])


def who(m):
    s = m.sender
    if s is None:
        return "?"
    name = " ".join(x for x in [getattr(s, "first_name", None), getattr(s, "last_name", None)] if x) or getattr(s, "title", None) or "?"
    u = getattr(s, "username", None)
    return f"{name} (@{u})" if u else name


def fmt(m):
    t = m.date.astimezone().strftime("%Y-%m-%d %H:%M")
    body = m.text or (f"[{m.file.mime_type or 'media'}]" if m.media else "[service]")
    return f"[{m.id}] {t} {'ME' if m.out else who(m)}: {body}"


async def resolve(cl, ref):
    if ref.lstrip("-").isdigit():
        return await cl.get_entity(int(ref))
    if ref.startswith("@") or ref.startswith("+") or "t.me/" in ref:
        return await cl.get_entity(ref)
    low = ref.lower()
    hits = [d for d in await cl.get_dialogs(limit=200) if low in (d.name or "").lower()]
    if not hits:
        sys.exit(f"chat not found: {ref}")
    if len(hits) > 1:
        exact = [d for d in hits if (d.name or "").lower() == low]
        if len(exact) != 1:
            sys.exit("ambiguous chat, candidates:\n" + "\n".join(f"  {d.id}  {d.name}" for d in hits[:10]))
        hits = exact
    return hits[0].entity


async def login():
    HOME.mkdir(parents=True, exist_ok=True)
    c = cfg() or {}
    if not c:
        print("Get api_id/api_hash at https://my.telegram.org -> API development tools")
        c = {"api_id": input("api_id: ").strip(), "api_hash": getpass.getpass("api_hash: ").strip()}
        CFG.write_text(json.dumps(c), "utf-8")
    cl = TelegramClient(SESSION, int(c["api_id"]), c["api_hash"])
    await cl.connect()
    if not await cl.is_user_authorized():
        phone = input("phone (+...): ").strip()
        await cl.send_code_request(phone)
        try:
            await cl.sign_in(phone, input("code: ").strip())
        except SessionPasswordNeededError:
            await cl.sign_in(password=getpass.getpass("2FA password: "))
    me = await cl.get_me()
    print(f"logged in as {me.first_name} (@{me.username})")
    await cl.disconnect()


async def run(a):
    cl = client()
    await cl.connect()
    try:
        if not await cl.is_user_authorized():
            print("NEED_LOGIN: run `tg login`", file=sys.stderr)
            sys.exit(EXIT_NEED_LOGIN)
        if a.cmd == "whoami":
            me = await cl.get_me()
            print(f"{me.first_name} @{me.username} id={me.id}")
        elif a.cmd == "chats":
            for d in await cl.get_dialogs(limit=a.limit):
                if a.unread and not d.unread_count:
                    continue
                print(f"{d.id}\t{d.name}\tunread={d.unread_count}")
        elif a.cmd == "read":
            ent = await resolve(cl, a.chat)
            msgs = [m async for m in cl.iter_messages(ent, limit=a.limit)]
            for m in reversed(msgs):
                print(fmt(m))
        elif a.cmd == "send":
            ent = await resolve(cl, a.chat)
            st = json.loads(SENDS.read_text()) if SENDS.exists() else {}
            today = time.strftime("%Y-%m-%d")
            if st.get("day") != today:
                st = {"day": today, "count": 0, "last": 0}
            if st["count"] >= SEND_DAILY_CAP:
                sys.exit(f"LIMIT: {SEND_DAILY_CAP} sends/day reached")
            if time.time() - st["last"] < SEND_MIN_INTERVAL:
                time.sleep(SEND_MIN_INTERVAL)
            name = getattr(ent, "title", None) or getattr(ent, "first_name", None) or str(ent.id)
            if not a.yes:
                print(f"DRY RUN: would send to '{name}': {a.text}\nre-run with --yes after the user approved this exact text and recipient")
                return
            m = await cl.send_message(ent, a.text, reply_to=a.reply_to)
            st["count"] += 1
            st["last"] = time.time()
            SENDS.write_text(json.dumps(st))
            print(f"sent to '{name}' as message {m.id}")
    finally:
        await cl.disconnect()


def main():
    ap = argparse.ArgumentParser(prog="tg")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login"); sub.add_parser("whoami")
    p = sub.add_parser("chats"); p.add_argument("--limit", type=int, default=30); p.add_argument("--unread", action="store_true")
    p = sub.add_parser("read"); p.add_argument("chat"); p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("send"); p.add_argument("chat"); p.add_argument("text")
    p.add_argument("--reply-to", type=int); p.add_argument("--yes", action="store_true", help="actually send (default is dry run)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(login() if a.cmd == "login" else run(a))


if __name__ == "__main__":
    main()
