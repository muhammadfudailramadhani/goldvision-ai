"""Telegram polling runner — bot nyata via Bot API (FASE 2).

Alur: getUpdates (long polling) -> handle_update (intent -> consent -> quota
-> analysis live Twelve Data -> chart -> reply) -> sendMessage/sendPhoto.

Endpoint Bot API yang dipakai (https://api.telegram.org/bot<TOKEN>/<method>):
  getMe       — validasi token saat startup
  getUpdates  — long polling pesan masuk (offset naik, tidak diproses ulang)
  sendMessage / sendPhoto — via HttpTransport adapter (§29: token hanya dari env)

Pemakaian:
    1. Isi TELEGRAM_BOT_TOKEN di .env (dapatkan dari @BotFather)
    2. python scripts/run_telegram.py

Kegagalan satu update TIDAK menghentikan bot — di-log lalu lanjut (skip).
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.chdir(Path(__file__).resolve().parent.parent)  # generated/ & db relatif ke repo root

import httpx  # noqa: E402

from app.channels.telegram.adapter import HttpTransport, TelegramAdapter  # noqa: E402
from app.channels.telegram.delivery.queue import RetryAfterError  # noqa: E402
from app.db import init_db  # noqa: E402
from app.settings import get_settings  # noqa: E402

API_BASE = "https://api.telegram.org"
POLL_TIMEOUT = 25  # detik long polling


def bot_url(token: str, method: str) -> str:
    return f"{API_BASE}/bot{token}/{method}"


async def get_me(token: str) -> dict:
    """getMe — validasi token. Raise RuntimeError bila token ditolak."""
    resp = await asyncio.to_thread(httpx.get, bot_url(token, "getMe"), timeout=15.0)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Token ditolak Telegram: {data.get('description', resp.status_code)}")
    return data["result"]


async def get_updates(token: str, offset: int) -> list[dict]:
    """getUpdates long polling — hanya update_id >= offset (yang belum diproses)."""
    resp = await asyncio.to_thread(
        httpx.get, bot_url(token, "getUpdates"),
        params={"offset": offset, "timeout": POLL_TIMEOUT, "allowed_updates": '["message"]'},
        timeout=POLL_TIMEOUT + 15.0,
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"getUpdates gagal: {data.get('description', resp.status_code)}")
    return data.get("result", [])


async def main() -> None:
    parser = argparse.ArgumentParser(description="GoldVision AI — Telegram polling runner")
    parser.add_argument("--once", action="store_true", help="proses satu batch lalu berhenti (debug)")
    args = parser.parse_args()

    s = get_settings()
    if not s.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN kosong.")
        print("Cara setup: buka Telegram -> @BotFather -> /newbot -> salin token ->")
        print("paste ke .env pada baris TELEGRAM_BOT_TOKEN=...")
        sys.exit(1)
    token = s.telegram_bot_token

    init_db()
    me = await get_me(token)
    print(f"Bot aktif: @{me.get('username')} (id {me.get('id')})")
    print(f"Market data mode: {s.market_data_mode} | Kirim /start lalu 'analisa gold' ke bot.")
    print("Polling... (Ctrl+C untuk berhenti)")

    adapter = TelegramAdapter(transport=HttpTransport(token))
    from app.channels.telegram.handlers.handler import handle_update

    offset = 0
    while True:
        try:
            updates = await get_updates(token, offset)
        except httpx.HTTPError as e:
            print(f"[net] getUpdates error, retry 5s: {e}")
            await asyncio.sleep(5)
            continue
        except RuntimeError as e:
            desc = str(e)
            if "409" in desc or "Conflict" in desc:
                print("[409] bot sedang di-poll dari tempat lain (webhook/poller lain). "
                      "Hentikan yang lain, retry 15s.")
                await asyncio.sleep(15)
                continue
            print(f"[err] {desc} — retry 10s")
            await asyncio.sleep(10)
            continue

        for upd in updates:
            offset = max(offset, upd["update_id"] + 1)
            try:
                result = await handle_update(upd, adapter=adapter)
                if result:
                    print(f"[ok] update={upd['update_id']} intent={result.intent} "
                          f"pair={result.pair or '-'} policy={result.policy}")
            except RetryAfterError as e:  # honor 429 — jangan bypass (§23)
                print(f"[429] retry_after={e.retry_after}s — pause lalu lanjut")
                await asyncio.sleep(e.retry_after)
            except Exception as e:  # noqa: BLE001 — satu update gagal = skip, bot tetap jalan
                print(f"[skip] update={upd['update_id']} error: {e}")

        if args.once:
            print("Mode --once selesai.")
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBerhenti.")
