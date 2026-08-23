"""Repositories — satu tempat untuk akses data, engine tidak menyentuh SQLAlchemy langsung."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, QuotaUsage, Signal, SignalDelivery, User


class UserRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_by_external_id(self, channel: str, external_id: str) -> User | None:
        return self.session.scalar(
            select(User).where(User.channel == channel, User.external_id == external_id)
        )

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def create(self, channel: str, external_id: str, **kwargs) -> User:
        user = User(channel=channel, external_id=external_id, **kwargs)
        self.session.add(user)
        self.session.flush()
        return user

    def eligible_for_broadcast(self) -> list[User]:
        """§39: hanya user started, aktif, notifications on."""
        return list(
            self.session.scalars(
                select(User).where(
                    User.is_active.is_(True),
                    User.notifications_enabled.is_(True),
                    User.started_bot_at.is_not(None),
                )
            )
        )


class QuotaRepo:
    def __init__(self, session: Session):
        self.session = session

    def count_since(self, user_id: int, since: datetime, kind: str = "live_analysis") -> int:
        return len(
            list(
                self.session.scalars(
                    select(QuotaUsage).where(
                        QuotaUsage.user_id == user_id,
                        QuotaUsage.kind == kind,
                        QuotaUsage.created_at >= since,
                    )
                )
            )
        )

    def consume(self, user_id: int, kind: str = "live_analysis") -> None:
        self.session.add(QuotaUsage(user_id=user_id, kind=kind))
        self.session.flush()


class SignalRepo:
    def __init__(self, session: Session):
        self.session = session

    def fingerprint_exists(self, fingerprint: str) -> bool:
        return self.session.scalar(select(Signal.id).where(Signal.fingerprint == fingerprint)) is not None

    def save(self, **kwargs) -> Signal:
        signal = Signal(**kwargs)
        self.session.add(signal)
        self.session.flush()
        return signal

    def recent_for_pair(self, pair: str, direction: str, within_minutes: int = 240):
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)
        return list(
            self.session.scalars(
                select(Signal).where(
                    Signal.pair == pair,
                    Signal.direction == direction,
                    Signal.created_at >= cutoff,
                )
            )
        )


class AuditRepo:
    def __init__(self, session: Session):
        self.session = session

    def record(self, **kwargs) -> AuditLog:
        entry = AuditLog(**kwargs)
        self.session.add(entry)
        self.session.flush()
        return entry

    def for_user(self, user_id: int) -> list[AuditLog]:
        return list(self.session.scalars(select(AuditLog).where(AuditLog.user_id == user_id)))


class DeliveryRepo:
    def __init__(self, session: Session):
        self.session = session

    def record(self, **kwargs) -> SignalDelivery:
        item = SignalDelivery(**kwargs)
        self.session.add(item)
        self.session.flush()
        return item
