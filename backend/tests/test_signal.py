"""Test signal engine (§25, §41) — fingerprint dedup & frequency control."""
from app.core.signal.engine import make_fingerprint
from app.channels.telegram.compliance.delivery_policy import classify_failure, should_stop_retrying


def test_fingerprint_deterministic():
    a = make_fingerprint("XAUUSD", "BUY", 2350.0, 2340.0, 2365.0, 2380.0, "M15")
    b = make_fingerprint("XAUUSD", "BUY", 2350.0, 2340.0, 2365.0, 2380.0, "M15")
    assert a == b


def test_fingerprint_differs_on_sl_change():
    a = make_fingerprint("XAUUSD", "BUY", 2350.0, 2340.0, 2365.0, 2380.0, "M15")
    b = make_fingerprint("XAUUSD", "BUY", 2350.0, 2345.0, 2365.0, 2380.0, "M15")
    assert a != b


def test_fingerprint_differs_on_direction():
    a = make_fingerprint("XAUUSD", "BUY", 2350.0, 2340.0, 2365.0, 2380.0, "M15")
    b = make_fingerprint("XAUUSD", "SELL", 2350.0, 2340.0, 2365.0, 2380.0, "M15")
    assert a != b


def test_rounding_tolerant():
    """Entry 2350.001 vs 2350.00 = sinyal sama (materially unchanged, §41)."""
    a = make_fingerprint("XAUUSD", "BUY", 2350.001, 2340.0, 2365.0, 2380.0, "M15")
    b = make_fingerprint("XAUUSD", "BUY", 2350.0, 2340.0, 2365.0, 2380.0, "M15")
    assert a == b


def test_delivery_policy_permanent():
    assert classify_failure("bot was blocked by user") == "PERMANENT"
    assert should_stop_retrying("bot was blocked by user", attempts=1)


def test_delivery_policy_temporary():
    assert classify_failure("network timeout") == "TEMPORARY"
    assert not should_stop_retrying("network timeout", attempts=1)
    assert should_stop_retrying("network timeout", attempts=3)
