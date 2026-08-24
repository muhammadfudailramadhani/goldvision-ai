"""Token bucket + leaky bucket rate limiter (§22).

Jangan sekadar time.sleep(1) — ini queue-aware dan retry-after-aware.
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Bucket:
    tokens: float
    max_tokens: float
    refill_rate: float  # tokens per second
    last_refill: float = field(default_factory=time.monotonic)

    def consume(self, n: int = 1) -> bool:
        self._refill()
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class RateLimiter:
    def __init__(self):
        self._buckets: dict[str, Bucket] = {}

    def _get(self, key: str, max_tokens: float, refill_rate: float) -> Bucket:
        if key not in self._buckets:
            self._buckets[key] = Bucket(max_tokens, max_tokens, refill_rate)
        return self._buckets[key]

    def check_chat(self, chat_id: str) -> bool:
        b = self._get(f"chat:{chat_id}", max_tokens=2, refill_rate=1.0)
        return b.consume()

    def check_group(self, chat_id: str) -> bool:
        b = self._get(f"grp:{chat_id}", max_tokens=20, refill_rate=20.0 / 60)
        return b.consume()

    def check_broadcast(self) -> bool:
        b = self._get("broadcast", max_tokens=30, refill_rate=30.0)
        return b.consume()

    def reset(self) -> None:
        self._buckets.clear()