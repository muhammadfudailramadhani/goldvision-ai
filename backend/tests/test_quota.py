"""Test QuotaService (§16) — server-side, FREE 3/minggu, VIP 4/hari."""
from datetime import datetime, timedelta, timezone

from app.core.quota.service import QuotaService
from app.repositories import UserRepo


def _make_user(session, plan="FREE", expires=None):
    repo = UserRepo(session)
    return repo.create("telegram", f"u-{plan}-{id(session)}-{datetime.now().timestamp()}",
                       plan=plan, plan_expires_at=expires)


def test_free_limit_3_per_week(db_session):
    user = _make_user(db_session)
    svc = QuotaService(db_session)
    results = [svc.consume(user).allowed for _ in range(4)]
    assert results == [True, True, True, False]  # ke-4 ditolak


def test_vip_limit_4_per_day(db_session):
    user = _make_user(db_session, plan="VIP",
                      expires=datetime.now(timezone.utc) + timedelta(days=30))
    svc = QuotaService(db_session)
    results = [svc.consume(user).allowed for _ in range(5)]
    assert results == [True, True, True, True, False]  # ke-5 ditolak


def test_expired_vip_falls_back_to_free(db_session):
    user = _make_user(db_session, plan="VIP",
                      expires=datetime.now(timezone.utc) - timedelta(days=1))
    svc = QuotaService(db_session)
    decision = svc.check(user)
    assert decision.plan == "FREE"
    assert decision.limit == 3


def test_quota_reason_has_block_code(db_session):
    user = _make_user(db_session)
    svc = QuotaService(db_session)
    for _ in range(3):
        svc.consume(user)
    decision = svc.check(user)
    assert not decision.allowed
    assert "SEND_BLOCKED_QUOTA" in decision.reason
