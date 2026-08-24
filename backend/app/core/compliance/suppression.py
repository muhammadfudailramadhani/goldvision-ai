"""Suppression universal (§36) — user yang tidak boleh dikirimi apa pun."""
from app.db import SessionLocal
from app.models import WhatsAppOptIn
from app.repositories import UserRepo


def is_suppressed(channel: str, external_id: str) -> bool:
    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id(channel, external_id)
        if user is None:
            return channel == "whatsapp"  # §33: tanpa opt-in record = suppressed untuk WhatsApp
        if channel == "whatsapp":
            rec = session.query(WhatsAppOptIn).filter_by(user_id=user.id).first()
            return bool(rec is None or rec.is_suppressed)
        return not user.is_active  # telegram: suppressed = blocked/inactive
    finally:
        session.close()
