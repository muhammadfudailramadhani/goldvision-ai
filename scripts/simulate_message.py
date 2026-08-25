"""Simulator pesan Telegram lokal (§48).

Pemakaian:
    python scripts/simulate_message.py "Gold sekarang bagaimana?"
    python scripts/simulate_message.py "Analisa EURUSD" --user 12345
Output format §48: Intent, Pair, Quota, Policy, Chart, Score, Action.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.chdir(Path(__file__).resolve().parent.parent)  # generated/ & db relatif ke repo root

# Console Windows (cp1252) tidak bisa mencetak emoji reply bot — paksa UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.channels.base import MessageContext  # noqa: E402
from app.channels.telegram.adapter import SimulatedTransport, TelegramAdapter  # noqa: E402
from app.channels.telegram.handlers.handler import TelegramHandler  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.repositories import UserRepo  # noqa: E402


async def main():
    parser = argparse.ArgumentParser(description="GoldVision AI — Telegram message simulator")
    parser.add_argument("message", help="pesan user, mis. 'Gold sekarang bagaimana?'")
    parser.add_argument("--user", default="1001", help="telegram user id (default 1001)")
    parser.add_argument("--fresh", action="store_true", help="reset quota user (dev)")
    args = parser.parse_args()

    init_db()
    transport = SimulatedTransport()
    adapter = TelegramAdapter(transport=transport)
    handler = TelegramHandler(adapter=adapter)

    # /start otomatis sekali supaya consent tercatat (§20)
    await handler.handle(MessageContext(user_id=args.user, channel="telegram",
                                        message_id="0", text="/start", chat_id=args.user))
    if args.fresh:
        session = SessionLocal()
        try:
            user = UserRepo(session).get_by_external_id("telegram", args.user)
            if user:
                from app.models import QuotaUsage
                for q in session.query(QuotaUsage).filter_by(user_id=user.id):
                    session.delete(q)
                session.commit()
        finally:
            session.close()

    ctx = MessageContext(user_id=args.user, channel="telegram",
                         message_id="1", text=args.message, chat_id=args.user)
    result = await handler.handle(ctx)

    print(f"Intent:\n{result.intent}\n")
    print(f"Pair:\n{result.pair or '-'}\n")
    print(f"Quota:\n{result.quota_used if result.quota_used is not None else '-'}/"
          f"{result.quota_limit if result.quota_limit is not None else '-'}\n")
    print(f"Policy:\n{result.policy}\n")
    print(f"Chart:\n{result.chart_path or '-'}\n")
    print(f"Score:\n{result.score if result.score is not None else '-'}\n")
    print(f"Action:\n{result.action or '-'}\n")
    print(f"Reply:\n{result.reply[:500]}")
    if result.chart_path and not Path(result.chart_path).exists():
        print(f"\n!! chart path dilaporkan tapi file tidak ada: {result.chart_path}")


if __name__ == "__main__":
    asyncio.run(main())
