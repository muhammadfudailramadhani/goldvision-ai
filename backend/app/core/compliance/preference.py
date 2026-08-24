"""Preference service (§42, §43) — quiet hours & notification prefs."""
from datetime import datetime, timezone

from app.db import SessionLocal
from app.repositories import UserRepo


def get_user_preferences(external_id: str, channel: str = "telegram") -> dict | None:
    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id(channel, external_id)
        if user is None:
            return None
        return {
            "notifications_enabled": user.notifications_enabled,
            "auto_signal_enabled": user.auto_signal_enabled,
            "quiet_hours_start": user.quiet_hours_start,
            "quiet_hours_end": user.quiet_hours_end,
            "timezone": user.timezone,
        }
    finally:
        session.close()


def in_quiet_hours(prefs: dict | None, now: datetime | None = None) -> bool:
    if not prefs or prefs.get("quiet_hours_start") is None or prefs.get("quiet_hours_end") is None:
        return False
    now = now or datetime.now(timezone.utc)
    hour = now.hour
    start, end = prefs["quiet_hours_start"], prefs["quiet_hours_end"]
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end
