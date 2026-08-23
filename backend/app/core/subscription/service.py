"""SubscriptionService — status plan user & ekspire."""
from datetime import datetime, timezone

from app.models import Plan
from app.repositories import UserRepo


class SubscriptionService:
    def __init__(self, session):
        self.users = UserRepo(session)

    def effective_plan(self, user) -> str:
        if user.plan == Plan.VIP.value and (
            user.plan_expires_at is None or user.plan_expires_at > datetime.now(timezone.utc)
        ):
            return "VIP"
        return "FREE"

    def upgrade(self, user_id: int, days: int = 30) -> str:
        user = self.users.get(user_id)
        if user is None:
            raise ValueError(f"user {user_id} tidak ditemukan")
        user.plan = Plan.VIP.value
        user.plan_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + __import__("datetime").timedelta(days=days)
        return "VIP"
