"""Delivery policy (§26) — klasifikasi kegagalan permanen vs sementara."""

PERMANENT_FAIL_SUBSTRINGS = ("blocked", "kicked", "chat not found", "unauthorized", "deactivated")
TEMPORARY_FAIL_SUBSTRINGS = ("timeout", "network", "temporarily", "flood", 429)


def classify_failure(error_text: str) -> str:
    """Return PERMANENT | TEMPORARY | UNKNOWN."""
    lower = str(error_text).lower()
    if any(s in lower for s in PERMANENT_FAIL_SUBSTRINGS):
        return "PERMANENT"
    if any(s in lower for s in ("timeout", "network", "temporarily")):
        return "TEMPORARY"
    if "flood" in lower or "429" in lower:
        return "RATE_LIMIT"
    return "UNKNOWN"


def should_stop_retrying(error_text: str, attempts: int, max_retries: int = 3) -> bool:
    kind = classify_failure(error_text)
    if kind == "PERMANENT":
        return True  # §26: jangan retry user yang permanen gagal
    return attempts >= max_retries
