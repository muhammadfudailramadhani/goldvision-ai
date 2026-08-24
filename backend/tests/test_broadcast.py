"""Test broadcast queue (§24, §46) — 1000 user, queue tidak meledak, dedup jalan."""
from app.channels.telegram.compliance.rate_policy import RatePolicy
from app.channels.telegram.delivery.queue import (
    BroadcastQueue, DeliveryItem, DeliveryReport, RetryAfterError)
from app.channels.telegram.rate_limit.bucket import RateLimiter


def _sender_ok(chat_id, item):
    return "mid-1"


def test_broadcast_1000_users_no_explosion():
    policy = RatePolicy(RateLimiter())
    queue = BroadcastQueue(_sender_ok, policy)
    report = DeliveryReport(broadcast_id="t1000")
    for i in range(1000):
        item = DeliveryItem(broadcast_id="t1000", user_id=i, chat_id=f"c{i}", text="sinyal")
        queue._queue.put_nowait(item)
    queue.drain(report)
    assert report.total == 1000
    assert report.sent + report.blocked + report.failed == 1000  # tidak ada yang hilang
    assert len(report.items) == 1000


def test_duplicate_fingerprint_rejected():
    policy = RatePolicy(RateLimiter())
    queue = BroadcastQueue(_sender_ok, policy, known_fingerprints={"fp-1"})
    item = DeliveryItem(broadcast_id="b", user_id=1, chat_id="c1", text="x", fingerprint="fp-1")
    accepted = queue.enqueue(item)
    assert not accepted  # §25: DO NOT SEND DUPLICATE


def test_429_retry_then_success():
    attempts = {"n": 0}

    def flaky(chat_id, item):
        attempts["n"] += 1
        if attempts["n"] <= 2:
            raise RetryAfterError(0.01)
        return "mid-ok"

    policy = RatePolicy(RateLimiter())
    queue = BroadcastQueue(flaky, policy, max_retries=3)
    report = DeliveryReport(broadcast_id="t429")
    queue._queue.put_nowait(DeliveryItem(broadcast_id="t429", user_id=1, chat_id="c1", text="x"))
    queue.drain(report)
    assert report.sent == 1 and report.retried == 2  # 429 dua kali lalu sukses


def test_429_gives_up_after_max_retry():
    def always_429(chat_id, item):
        raise RetryAfterError(0.01)

    policy = RatePolicy(RateLimiter())
    queue = BroadcastQueue(always_429, policy, max_retries=3)
    report = DeliveryReport(broadcast_id="t429x")
    queue._queue.put_nowait(DeliveryItem(broadcast_id="t429x", user_id=1, chat_id="c1", text="x"))
    queue.drain(report)
    assert report.sent == 0
    assert report.failed >= 1  # berhenti, bukan infinite retry (§46)
