"""WhatsApp service window (§34) — 24 jam sejak pesan masuk terakhir dari user.

Free-form hanya dalam window; di luar window wajib template approved.
"""
from datetime import datetime, timedelta, timezone


def is_within_service_window(last_inbound_at: datetime | None,
                             window_hours: int = 24) -> bool:
    if last_inbound_at is None:
        return False
    if last_inbound_at.tzinfo is None:
        last_inbound_at = last_inbound_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_inbound_at <= timedelta(hours=window_hours)
