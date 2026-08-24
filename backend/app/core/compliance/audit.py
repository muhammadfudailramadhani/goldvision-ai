"""Universal audit (§44) — semua keputusan pengiriman penting tercatat."""
from app.db import SessionLocal
from app.repositories import AuditRepo


def record(user_id: int | None, channel: str, action: str, *,
           message_type: str = "", reason: str = "",
           policy_result: str = "", rate_limit_result: str = "",
           delivery_status: str = "") -> None:
    session = SessionLocal()
    try:
        AuditRepo(session).record(
            user_id=user_id, channel=channel, action=action,
            message_type=message_type, reason=reason,
            policy_result=policy_result, rate_limit_result=rate_limit_result,
            delivery_status=delivery_status)
        session.commit()
    finally:
        session.close()


def history(user_id: int) -> list:
    session = SessionLocal()
    try:
        return AuditRepo(session).for_user(user_id)
    finally:
        session.close()
