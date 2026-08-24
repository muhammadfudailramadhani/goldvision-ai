"""Local broadcast simulator (§50) — TIDAK mengirim ke Telegram production.

    python scripts/demo_broadcast.py --users 100
    python scripts/demo_broadcast.py --users 1000 --with-429
"""
import argparse
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.chdir(Path(__file__).resolve().parent.parent)

from app.channels.telegram.compliance.rate_policy import RatePolicy  # noqa: E402
from app.channels.telegram.delivery.queue import (  # noqa: E402
    BroadcastQueue, DeliveryItem, DeliveryReport, RetryAfterError)
from app.channels.telegram.rate_limit.bucket import RateLimiter  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.repositories import UserRepo  # noqa: E402


def seed_users(n: int) -> tuple[list, list, list]:
    """Return (eligible, blocked, opted_out) chat ids."""
    session = SessionLocal()
    try:
        repo = UserRepo(session)
        eligible, blocked, opted_out = [], [], []
        for i in range(1, n + 1):
            ext = f"bc-{i}"
            user = repo.get_by_external_id("telegram", ext)
            if user is None:
                user = repo.create("telegram", ext, started_bot_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
            session.commit()
            if i % 10 == 3:      # ~10% blocked
                user.is_active = False
                blocked.append(ext)
            elif i % 10 == 7:    # ~10% opt-out
                user.notifications_enabled = False
                opted_out.append(ext)
            else:
                eligible.append(ext)
        session.commit()
        return eligible, blocked, opted_out
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Broadcast queue simulator (localhost)")
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--with-429", action="store_true", help="simulasikan 429 pada sekitar 5 persen pengiriman")
    args = parser.parse_args()

    init_db()
    random.seed(42)
    eligible, blocked, opted_out = seed_users(args.users)

    sent_log: list[str] = []

    def sender(chat_id: str, item: DeliveryItem) -> str:
        if args.with_429 and random.random() < 0.05:
            raise RetryAfterError(2.0)
        sent_log.append(chat_id)
        return f"sim-{len(sent_log)}"

    policy = RatePolicy(RateLimiter())
    queue = BroadcastQueue(sender, policy)
    report = DeliveryReport(broadcast_id="demo-bc-001")

    fp = "fingerprint-demo-v1"
    queued = 0
    for ext in eligible:  # §39: hanya eligible yang masuk antrian
        item = DeliveryItem(broadcast_id="demo-bc-001", user_id=0, chat_id=ext,
                            text="signal demo", fingerprint=None)
        queue._queue.put_nowait(item)  # sync untuk simulator
        queued += 1

    # contoh dedup §25: fingerprint yang sudah pernah terkirim = ditolak
    queue.known_fingerprints.add(fp)
    dup_item = DeliveryItem(broadcast_id="demo-bc-001", user_id=0, chat_id=eligible[0],
                            text="signal demo", fingerprint=fp)
    accepted = queue.enqueue(dup_item)

    queue.drain(report)

    print(f"Seeded users : {args.users}")
    print(f"Eligible     : {len(eligible)}")
    print(f"Blocked      : {len(blocked)} (tidak masuk antrian — §39)")
    print(f"Opted out    : {len(opted_out)} (tidak masuk antrian — §39)")
    print(f"Queued       : {queued}")
    print(f"Duplicate    : {'ditolak (PASS)' if not accepted else 'DITERIMA (FAIL)'}")
    print(f"Sent         : {report.sent}")
    print(f"Retried(429) : {report.retried}")
    print(f"Failed       : {report.failed}")
    print(f"Blocked RL   : {report.blocked}")
    print(f"\n{report.summary_line()}")
    assert len(sent_log) == report.sent, "sent_log harus sama dengan report.sent"
    print("\nRESULT: PASS" if report.sent > 0 else "\nRESULT: FAIL (tidak ada yang terkirim)")


if __name__ == "__main__":
    main()
