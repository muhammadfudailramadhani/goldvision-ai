"""Test rate limiter (§22) + 429 handling (§23) — tidak ada bypass, tidak ada infinite retry."""
from app.channels.telegram.compliance.rate_policy import RatePolicy, handle_429
from app.channels.telegram.rate_limit.bucket import RateLimiter


def test_chat_rate_limit_blocks_burst():
    policy = RatePolicy(RateLimiter())
    results = [policy.check_outgoing("c1").allowed for _ in range(5)]
    assert results[0] and results[1]           # burst capacity 2
    assert not all(results[2:])                # sisanya diblok sampai refill


def test_group_rate_limit_20_per_min():
    policy = RatePolicy(RateLimiter())
    ok = 0
    for _ in range(25):
        if policy.check_outgoing("g1", is_group=True).allowed:
            ok += 1
    assert ok <= 20 + 2  # 20 group + slack chat bucket


def test_429_honors_retry_after():
    d = handle_429(retry_after=7.0, attempts=0)
    assert d.allowed and d.retry_after == 7.0


def test_429_stops_after_max_retry():
    d = handle_429(retry_after=7.0, attempts=3)
    assert not d.allowed and "max retry" in d.reason


def test_429_no_bypass():
    """§23/§38: tidak ada opsi rotate token/bot — hanya retry atau gagal."""
    all_decisions = [handle_429(3.0, attempts=a) for a in range(10)]
    assert all(d.retry_after >= 3.0 for d in all_decisions)  # selalu menunggu, tak pernah curang
