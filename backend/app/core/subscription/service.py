"""SubscriptionService — status plan user, upgrade VIP (sandbox §18), ekspire."""
from datetime import datetime, timedelta, timezone

from app.models import Plan
from app.repositories import UserRepo


def _as_aware_utc(dt: datetime) -> datetime:
    """SQLite menyimpan naive-UTC — normalisasi sebelum dibandingkan."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


class SubscriptionService:
    def __init__(self, session):
        self.session = session
        self.users = UserRepo(session)

    def effective_plan(self, user) -> str:
        if user.plan == Plan.VIP.value and (
            user.plan_expires_at is None
            or _as_aware_utc(user.plan_expires_at) > datetime.now(timezone.utc)
        ):
            return "VIP"
        return "FREE"

    def upgrade(self, user_id: int, days: int = 30) -> str:
        user = self.users.get(user_id)
        if user is None:
            raise ValueError(f"user {user_id} tidak ditemukan")
        return self._grant(user, days)

    def upgrade_by_external(self, external_id: str, days: int = 30,
                            channel: str = "telegram") -> str:
        user = self.users.get_by_external_id(channel, external_id)
        if user is None:
            raise ValueError(f"user {external_id} tidak ditemukan")
        return self._grant(user, days)

    def _grant(self, user, days: int) -> str:
        """PAYMENT_MODE=sandbox: aktivasi manual oleh admin (§18).
        Payment gateway asli = FASE 3 saat kredensial tersedia.
        Simpan NAIVE-UTC (konvensi sqlite) agar konsisten setelah restart."""
        now = datetime.now(timezone.utc)
        base = user.plan_expires_at
        base = _as_aware_utc(base) if base else now
        if base < now:
            base = now
        user.plan = Plan.VIP.value
        user.plan_expires_at = (base + timedelta(days=days)).replace(tzinfo=None)
        self.session.commit()
        return "VIP"
