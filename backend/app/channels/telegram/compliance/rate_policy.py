"""Rate policy (§22, §23) — keputusan berdasarkan limit, bukan sleep buta."""
from dataclasses import dataclass

from ..config import limits
from ..rate_limit.bucket import RateLimiter


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    layer: str      # "chat" | "group" | "broadcast"
    retry_after: float = 0.0
    reason: str = ""


class RatePolicy:
    def __init__(self, limiter: RateLimiter | None = None):
        self.limiter = limiter or RateLimiter()

    def check_outgoing(self, chat_id: str, is_group: bool = False) -> RateDecision:
        if is_group:
            if not self.limiter.check_group(chat_id):
                return RateDecision(False, "group", 60.0,
                                    "SEND_BLOCKED_RATE_LIMIT: 20 msg/min group")
            # group juga tunduk pada limit per-chat 1 msg/s
        if not self.limiter.check_chat(chat_id):
            return RateDecision(False, "chat", 1.0,
                                "SEND_BLOCKED_RATE_LIMIT: 1 msg/s per chat")
        return RateDecision(True, "chat" if not is_group else "group")

    def check_bulk(self) -> RateDecision:
        if not self.limiter.check_broadcast():
            return RateDecision(False, "broadcast", 1.0,
                                "SEND_BLOCKED_RATE_LIMIT: 30 msg/s bulk")
        return RateDecision(True, "broadcast")


def handle_429(retry_after: float | None, attempts: int,
               max_retries: int | None = None) -> RateDecision:
    """§23: baca retry_after, jangan bypass dengan rotating bot/token (§38)."""
    max_retries = max_retries if max_retries is not None else limits.MAX_RETRY_429
    wait = retry_after if retry_after and retry_after > 0 else limits.DEFAULT_RETRY_AFTER_SEC
    if attempts >= max_retries:
        return RateDecision(False, "chat", wait,
                            f"SEND_FAILED: max retry ({max_retries}) tercapai setelah 429")
    return RateDecision(True, "chat", wait, f"RETRY_AFTER: {wait}s (attempt {attempts + 1})")
