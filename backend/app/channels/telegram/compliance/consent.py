"""Telegram consent (§20).

Bot tidak bisa memulai percakapan — user harus /start dulu.
User yang belum pernah memulai chat: DO NOT SEND.
"""
from datetime import datetime, timezone

from app.db import SessionLocal
from app.repositories import UserRepo


def check_user_consented(channel: str, external_id: str) -> bool:
    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id(channel, external_id)
        return user is not None and user.started_bot_at is not None and user.is_active
    finally:
        session.close()


def register_consent(channel: str, external_id: str) -> None:
    session = SessionLocal()
    try:
        repo = UserRepo(session)
        user = repo.get_by_external_id(channel, external_id)
        if user is None:
            user = repo.create(channel, external_id)
        if user.started_bot_at is None:
            user.started_bot_at = datetime.now(timezone.utc)
        user.is_active = True
        session.commit()
    finally:
        session.close()
