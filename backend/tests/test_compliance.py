"""Test universal compliance policy (§37) + audit trail (§44)."""
from datetime import datetime, timezone

from app.core.compliance.policy import PolicyDeps, UniversalMessagePolicy
from app.repositories import AuditRepo


def _policy():
    return UniversalMessagePolicy()


def test_allowed_when_all_ok():
    d = _policy().evaluate(PolicyDeps())
    assert d.allowed and d.reason == "SEND_ALLOWED"


def test_blocked_no_consent():
    d = _policy().evaluate(PolicyDeps(has_consent=False))
    assert not d.allowed and d.reason == "SEND_BLOCKED_NO_CONSENT"


def test_blocked_opt_out():
    d = _policy().evaluate(PolicyDeps(notifications_enabled=False))
    assert not d.allowed and d.reason == "SEND_BLOCKED_OPT_OUT"


def test_blocked_suppressed():
    d = _policy().evaluate(PolicyDeps(is_suppressed=True))
    assert not d.allowed and d.reason == "SEND_BLOCKED_SUPPRESSED"


def test_blocked_rate_limit():
    d = _policy().evaluate(PolicyDeps(rate_limit_ok=False))
    assert not d.allowed and d.reason == "SEND_BLOCKED_RATE_LIMIT"


def test_blocked_duplicate():
    d = _policy().evaluate(PolicyDeps(is_duplicate=True))
    assert not d.allowed and d.reason == "SEND_BLOCKED_DUPLICATE"


def test_quiet_hours_same_day():
    policy = _policy()
    now = datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc)
    d = policy.evaluate(PolicyDeps(), now=now, quiet_start=22, quiet_end=6)
    assert not d.allowed and d.reason == "SEND_BLOCKED_QUIET_HOURS"


def test_quiet_hours_overnight_wrap():
    policy = _policy()
    jam3pagi = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
    blocked = policy.evaluate(PolicyDeps(), now=jam3pagi, quiet_start=22, quiet_end=6)
    siang = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    allowed = policy.evaluate(PolicyDeps(), now=siang, quiet_start=22, quiet_end=6)
    assert not blocked.allowed and blocked.reason == "SEND_BLOCKED_QUIET_HOURS"
    assert allowed.allowed


def test_audit_recorded(db_session):
    repo = AuditRepo(db_session)
    repo.record(user_id=1, channel="telegram", action="SEND",
                policy_result="SEND_BLOCKED_DUPLICATE", delivery_status="SKIPPED")
    db_session.commit()
    entries = repo.for_user(1)
    assert len(entries) == 1
    assert entries[0].policy_result == "SEND_BLOCKED_DUPLICATE"
