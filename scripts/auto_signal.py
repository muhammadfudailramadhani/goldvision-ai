"""Auto-signal scheduler (§24) — loop scan -> broadcast ke eligible users.

Pemakaian:
    python scripts/auto_signal.py --interval 900      # tiap 15 menit
    python scripts/auto_signal.py --once              # sekali (cron-friendly)

Kepatuhan: hanya user eligible (started+active+notifications on, §39),
fingerprint dedup §25, rate limit & 429 honor §22-23 via BroadcastQueue.
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.chdir(Path(__file__).resolve().parent.parent)

from app.channels.telegram.adapter import TelegramAdapter  # noqa: E402
from app.channels.telegram.compliance.rate_policy import RatePolicy  # noqa: E402
from app.channels.telegram.config.messages import SIGNAL_FORMAT  # noqa: E402
from app.channels.telegram.delivery.queue import (  # noqa: E402
    BroadcastQueue, DeliveryItem, DeliveryReport)
from app.core.market.provider import get_provider  # noqa: E402
from app.core.signals.scan import scan_pairs  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.repositories import UserRepo  # noqa: E402


def format_signal(signal) -> str:
    rr = abs(signal.tp2 - signal.entry) / max(abs(signal.entry - signal.sl), 1e-9)
    return SIGNAL_FORMAT.format(
        direction=signal.direction, pair=signal.pair, entry=signal.entry,
        sl=signal.sl, tp1=signal.tp1, tp2=signal.tp2, score=signal.score, rr=rr)


def broadcast_new_signals(new_signals, adapter) -> DeliveryReport:
    """Antre sinyal baru ke eligible users (§39)."""
    session = SessionLocal()
    try:
        eligible = UserRepo(session).eligible_for_broadcast()
    finally:
        session.close()

    def sender(chat_id: str, item) -> str:
        return adapter.send_text(chat_id, item.text) or ""

    queue = BroadcastQueue(sender, RatePolicy())
    report = DeliveryReport(broadcast_id=f"auto-{datetime.now(timezone.utc):%Y%m%d%H%M%S}")
    for sig in new_signals:
        for user in eligible:
            queue.enqueue(DeliveryItem(
                broadcast_id=report.broadcast_id, user_id=user.id,
                chat_id=user.external_id, text=format_signal(sig),
                fingerprint=f"{sig.fingerprint}:{user.id}"))
    queue.drain(report)
    return report


async def run_once() -> None:
    init_db()
    provider = get_provider()
    session = SessionLocal()
    try:
        new_signals = await scan_pairs(provider, session)
    finally:
        session.close()
    if not new_signals:
        print(f"[{datetime.now(timezone.utc):%H:%M:%S}] scan: tidak ada sinyal baru.")
        return
    adapter = TelegramAdapter()
    report = broadcast_new_signals(new_signals, adapter)
    print(f"[{datetime.now(timezone.utc):%H:%M:%S}] {len(new_signals)} sinyal baru -> "
          f"{report.summary_line()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="GoldVision auto-signal scheduler")
    parser.add_argument("--interval", type=int, default=900,
                        help="detik antar scan (default 900)")
    parser.add_argument("--once", action="store_true", help="scan sekali lalu keluar")
    args = parser.parse_args()

    if args.once:
        asyncio.run(run_once())
        return
    print(f"Auto-signal aktif, interval {args.interval}s. Ctrl+C untuk berhenti.")
    while True:
        try:
            asyncio.run(run_once())
        except Exception as e:  # noqa: BLE001 — scheduler tidak boleh mati
            print(f"[err] {e}")
        asyncio.run(asyncio.sleep(args.interval))


if __name__ == "__main__":
    main()
