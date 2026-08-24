"""WhatsApp opt-in (§33) — tabel whatsapp_opt_in sudah ada di models.

Opt-out = DO NOT SEND + suppression list. Dipakai saat channel diaktifkan.
"""
from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import WhatsAppOptIn
from app.repositories import UserRepo


def record_opt_in(phone: str, source: str = "unknown", category: str = "signal") -> None:
    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id("whatsapp", phone)
        if user is None:
            user = UserRepo(session).create("whatsapp", phone)
        existing = session.query(WhatsAppOptIn).filter_by(user_id=user.id).first()
        if existing is None:
            session.add(WhatsAppOptIn(
                user_id=user.id, opt_in_source=source,
                opt_in_timestamp=datetime.now(timezone.utc),
                opt_in_category=category, is_suppressed=False))
        else:
            existing.opt_in_timestamp = datetime.now(timezone.utc)
            existing.opt_out_timestamp = None
            existing.is_suppressed = False
        session.commit()
    finally:
        session.close()


def record_opt_out(phone: str) -> None:
    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id("whatsapp", phone)
        if user is None:
            return
        rec = session.query(WhatsAppOptIn).filter_by(user_id=user.id).first()
        if rec:
            rec.opt_out_timestamp = datetime.now(timezone.utc)
            rec.is_suppressed = True
        session.commit()
    finally:
        session.close()


def is_opted_in(phone: str) -> bool:
    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id("whatsapp", phone)
        if user is None:
            return False
        rec = session.query(WhatsAppOptIn).filter_by(user_id=user.id).first()
        return bool(rec and rec.opt_in_timestamp is not None and not rec.is_suppressed)
    finally:
        session.close()
