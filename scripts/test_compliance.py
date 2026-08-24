"""Local compliance simulator (§49) — 8 skenario, semua harus PASS.

    python scripts/test_compliance.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.chdir(Path(__file__).resolve().parent.parent)

from app.core.compliance.policy import PolicyDeps, UniversalMessagePolicy  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Plan, User  # noqa: E402
from app.repositories import UserRepo  # noqa: E402
from app.core.quota.service import QuotaService  # noqa: E402


def scenario_allowed(policy):
    d = policy.evaluate(PolicyDeps())
    return d.allowed and d.reason == "SEND_ALLOWED"


def scenario_blocked_user(policy):
    d = policy.evaluate(PolicyDeps(is_active=False))
    return (not d.allowed) and d.reason == "SEND_BLOCKED_INACTIVE"


def scenario_opt_out(policy):
    d = policy.evaluate(PolicyDeps(notifications_enabled=False))
    return (not d.allowed) and d.reason == "SEND_BLOCKED_OPT_OUT"


def scenario_suppressed(policy):
    d = policy.evaluate(PolicyDeps(is_suppressed=True))
    return (not d.allowed) and d.reason == "SEND_BLOCKED_SUPPRESSED"


def scenario_rate_limit(policy):
    d = policy.evaluate(PolicyDeps(rate_limit_ok=False))
    return (not d.allowed) and d.reason == "SEND_BLOCKED_RATE_LIMIT"


def scenario_duplicate(policy):
    d = policy.evaluate(PolicyDeps(is_duplicate=True))
    return (not d.allowed) and d.reason == "SEND_BLOCKED_DUPLICATE"


def scenario_quiet_hours(policy):
    now = datetime(2026, 1, 1, 23, 30, tzinfo=timezone.utc)
    d = policy.evaluate(PolicyDeps(), now=now, quiet_start=22, quiet_end=6)
    return (not d.allowed) and d.reason == "SEND_BLOCKED_QUIET_HOURS"


def scenario_quota_exceeded():
    session = SessionLocal()
    try:
        users = UserRepo(session)
        user = users.get_by_external_id("telegram", "quota-test-user")
        if user is None:
            user = users.create("telegram", "quota-test-user")
            session.commit()
        # habiskan 3 quota FREE
        quota = QuotaService(session)
        for _ in range(3):
            quota.consume(user)
        decision = quota.check(user)
        session.rollback()
        return (not decision.allowed) and "QUOTA" in decision.reason
    finally:
        session.close()


def main():
    init_db()
    policy = UniversalMessagePolicy()
    scenarios = [
        ("1. Allowed user", lambda: scenario_allowed(policy)),
        ("2. Blocked user", lambda: scenario_blocked_user(policy)),
        ("3. Opt-out user", lambda: scenario_opt_out(policy)),
        ("3b. Suppressed user", lambda: scenario_suppressed(policy)),
        ("4. Duplicate signal", lambda: scenario_duplicate(policy)),
        ("5. Rate limit", lambda: scenario_rate_limit(policy)),
        ("6. Quota exceeded", scenario_quota_exceeded),
        ("7. Quiet hours", lambda: scenario_quiet_hours(policy)),
        ("8. 429 retry honored", _scenario_429),
    ]
    all_pass = True
    for name, fn in scenarios:
        try:
            ok = fn()
        except Exception as e:  # noqa: BLE001
            print(f"ERROR  {name}: {e}")
            all_pass = False
            continue
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        all_pass = all_pass and ok
    print("\nRESULT:", "ALL PASS" if all_pass else "THERE ARE FAILURES")
    sys.exit(0 if all_pass else 1)


def _scenario_429():
    from app.channels.telegram.compliance.rate_policy import handle_429
    ok = handle_429(retry_after=3.0, attempts=0)
    stop = handle_429(retry_after=3.0, attempts=3)
    return ok.allowed and (not stop.allowed) and "max retry" in stop.reason


if __name__ == "__main__":
    main()
