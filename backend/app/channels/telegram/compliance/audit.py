"""Telegram audit log (§30, §44).Semua admin action dicatat.
"""
from datetime import datetime, timezone

from app.db import SessionLocal
from app.repositories import AuditRepo


def log_delivery(user_id: int | None, channel: str, action: str,
                message_type: str = "", policy_result: str = "",
                delivery_status: str = "", reason: str = "") -> None:
    session = SessionLocal()
    try:
        AuditRepo(session).record(
            user_id=user_id, channel=channel, action=action,
            message_type=message_type, policy_result=policy_result,
            delivery_status=delivery_status, reason=reason,
        )
        session.commit()
    finally:
        session.close()


def log_admin_action(admin_id: int, action: str, target: str = "", detail: str = "") -> None:
    log_delivery(
        user_id=admin_id, channel="telegram", action=f"ADMIN:{action}",
        message_type="admin_command", delivery_status="EXECUTED",
        reason=target + (": " + detail if detail else ""),
    )
