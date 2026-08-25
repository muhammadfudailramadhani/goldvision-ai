"""Delivery policy (§26) — klasifikasi kegagalan permanen vs sementara."""

PERMANENT_FAIL_SUBSTRINGS = ("blocked", "kicked", "chat not found", "unauthorized", "deactivated")
TEMPORARY_FAIL_SUBSTRINGS = ("timeout", "network", "temporarily")
RATE_LIMIT_SUBSTRINGS = ("flood", "429", "too many requests")


def classify_failure(error_text: str) -> str:
    """Return PERMANENT | TEMPORARY | RATE_LIMIT | UNKNOWN."""
    lower = str(error_text).lower()
    if any(s in lower for s in PERMANENT_FAIL_SUBSTRINGS):
        return "PERMANENT"
    if any(s in lower for s in TEMPORARY_FAIL_SUBSTRINGS):
        return "TEMPORARY"
    if any(s in lower for s in RATE_LIMIT_SUBSTRINGS):
        return "RATE_LIMIT"
    return "UNKNOWN"


def should_stop_retrying(error_text: str, attempts: int, max_retries: int = 3) -> bool:
    kind = classify_failure(error_text)
    if kind == "PERMANENT":
        return True  # §26: jangan retry user yang permanen gagal
    return attempts >= max_retries
