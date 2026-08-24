"""Telegram feature flags (§7)."""

from app.settings import get_settings


def is_enabled() -> bool:
    return get_settings().telegram_enabled


def admin_ids() -> list[str]:
    raw = get_settings().telegram_admin_id
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def is_admin(user_id: str) -> bool:
    return user_id in admin_ids()
