"""QuotaService (§16) — dihitung server-side, tidak percaya claim client.

FREE: 3 live analysis / 7 hari berjalan. VIP: 4 live analysis / hari (UTC).
Command ringan (/help /status /limit /subscription) tidak mengonsumsi quota.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.models import Plan
from app.repositories import QuotaRepo, UserRepo

LIMITS = {"FREE": (3, "7 hari"), "VIP": (4, "hari")}


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    plan: str
    used: int
    limit: int
    window: str
    reason: str


class QuotaService:
    def __init__(self, session):
        self.session = session
        self.users = UserRepo(session)
        self.quota = QuotaRepo(session)

    def _plan(self, user) -> str:
        if user.plan == Plan.VIP.value and (
            user.plan_expires_at is None or user.plan_expires_at > datetime.now(timezone.utc)
        ):
            return "VIP"
        return "FREE"

    def check(self, user) -> QuotaDecision:
        plan = self._plan(user)
        limit, window = LIMITS[plan]
        since = (datetime.now(timezone.utc) - (timedelta(days=7) if plan == "FREE" else timedelta(days=1)))
        used = self.quota.count_since(user.id, since)
        if used >= limit:
            return QuotaDecision(False, plan, used, limit, window,
                                 f"SEND_BLOCKED_QUOTA: limit {limit}/{window} tercapai")
        return QuotaDecision(True, plan, used, limit, window, "ALLOWED")

    def consume(self, user) -> QuotaDecision:
        decision = self.check(user)
        if decision.allowed:
            self.quota.consume(user.id)
            self.session.commit()
            return QuotaDecision(True, decision.plan, decision.used + 1, decision.limit, decision.window, "ALLOWED")
        return decision
