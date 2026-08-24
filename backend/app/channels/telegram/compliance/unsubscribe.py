"""Unsubscribe / user block (§26, §21).

User block bot / opt-out -> notifications_enabled=false, is_active=false.
Jangan terus retry user yang permanen gagal.
"""
from app.db import SessionLocal
from app.repositories import UserRepo


def mark_blocked(external_id: str, channel: str = "telegram") -> None:
    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id(channel, external_id)
        if user:
            user.notifications_enabled = False
            user.is_active = False
            session.commit()
    finally:
        session.close()


def disable_notifications(external_id: str, channel: str = "telegram") -> None:
    """Opt-out notifikasi TANPA menonaktifkan interaksi manual (§21)."""
    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id(channel, external_id)
        if user:
            user.notifications_enabled = False
            session.commit()
    finally:
        session.close()


def enable_notifications(external_id: str, channel: str = "telegram") -> None:
    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id(channel, external_id)
        if user:
            user.notifications_enabled = True
            session.commit()
    finally:
        session.close()
