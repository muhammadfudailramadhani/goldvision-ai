"""Set/delete webhook Telegram (FASE 2+) — alternatif polling.

Pemakaian:
    python scripts/set_webhook.py --set https://domainmu.com/webhook/telegram
    python scripts/set_webhook.py --info
    python scripts/set_webhook.py --delete

Syarat: TELEGRAM_BOT_TOKEN di .env. Sangat disarankan isi TELEGRAM_WEBHOOK_SECRET
(sama dengan app/main.py cek header X-Telegram-Bot-Api-Secret-Token).
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.chdir(Path(__file__).resolve().parent.parent)

import httpx  # noqa: E402

from app.settings import get_settings  # noqa: E402


def call(token: str, method: str, payload: dict) -> dict:
    resp = httpx.post(f"https://api.telegram.org/bot{token}/{method}",
                      json=payload, timeout=20.0)
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    if not data.get("ok"):
        sys.exit(1)
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Telegram webhook management")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--set", metavar="URL", help="pasang webhook (harus HTTPS)")
    group.add_argument("--delete", action="store_true", help="hapus webhook")
    group.add_argument("--info", action="store_true", help="lihat status webhook")
    args = parser.parse_args()

    s = get_settings()
    if not s.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN kosong di .env.")
        sys.exit(1)

    if args.info:
        call(s.telegram_bot_token, "getWebhookInfo", {})
    elif args.delete:
        call(s.telegram_bot_token, "deleteWebhook", {"drop_pending_updates": False})
        print("Webhook dihapus — polling (run_telegram.py) bisa dipakai lagi.")
    else:
        payload = {"url": args.set, "allowed_updates": ["message", "callback_query"],
                   "drop_pending_updates": False}
        if s.telegram_webhook_secret:
            payload["secret_token"] = s.telegram_webhook_secret
        call(s.telegram_bot_token, "setWebhook", payload)
        print("Webhook terpasang." + ("" if s.telegram_webhook_secret else
              "\nPERINGATAN: TELEGRAM_WEBHOOK_SECRET kosong — endpoint tanpa secret!"))


if __name__ == "__main__":
    main()
