from datetime import datetime, timezone
from enum import Enum as StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Plan(StrEnum):
    FREE = "FREE"
    VIP = "VIP"


class User(Base):
    __table_args__ = (UniqueConstraint("channel", "external_id", name="uq_user_channel_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(20))  # "telegram" | "whatsapp"
    external_id: Mapped[str] = mapped_column(String(64))  # telegram_user_id / phone number
    started_bot_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_signal_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # §43 preferensi
    quiet_hours_start: Mapped[int | None] = mapped_column(Integer)  # 0-23
    quiet_hours_end: Mapped[int | None] = mapped_column(Integer)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    language: Mapped[str] = mapped_column(String(10), default="id")
    plan: Mapped[str] = mapped_column(String(10), default=Plan.FREE.value)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WhatsAppOptIn(Base):
    """§33: opt-in WhatsApp — dipakai nanti saat channel diaktifkan."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    opt_in_source: Mapped[str | None] = mapped_column(String(100))
    opt_in_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opt_in_category: Mapped[str | None] = mapped_column(String(50))
    opt_out_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_suppressed: Mapped[bool] = mapped_column(Boolean, default=False)


class QuotaUsage(Base):
    """Satu baris = satu konsumsi live analysis (server-side, §16)."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30), default="live_analysis")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Signal(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pair: Mapped[str] = mapped_column(String(12))
    direction: Mapped[str] = mapped_column(String(6))  # BUY | SELL
    timeframe: Mapped[str] = mapped_column(String(6))
    entry: Mapped[float]
    sl: Mapped[float]
    tp1: Mapped[float]
    tp2: Mapped[float]
    score: Mapped[int]
    # §25: fingerprint dedup — identik = DO NOT SEND DUPLICATE
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SignalDelivery(Base):
    """§24: state pengiriman per user per broadcast."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    broadcast_id: Mapped[str] = mapped_column(String(40), index=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signal.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    message_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="QUEUED")  # QUEUED|SENT|FAILED|BLOCKED|SKIPPED
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(String(200))


class AuditLog(Base):
    """§44: setiap keputusan pengiriman penting tercatat."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    channel: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(40))
    message_type: Mapped[str | None] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(String(200))
    policy_result: Mapped[str | None] = mapped_column(String(40))
    rate_limit_result: Mapped[str | None] = mapped_column(String(40))
    delivery_status: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
