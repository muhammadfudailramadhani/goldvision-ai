"""Universal abuse guard (§36, §38) — mencegah pelanggaran, bukan menyamarkan.

Juga guard prompt-injection untuk konten yang dihasilkan AI (FASE 2):
output AI yang akan dikirim ke user divalidasi di sini.
"""
FORBIDDEN_OUTBOUND = [
    "guaranteed profit", "pasti untung", "pasti profit", "100% win",
    "no loss", "zero risk", "jaminan untung",
]

INJECTION_MARKERS = [
    "ignore previous instructions", "ignore all previous",
    "system prompt", "disregard above", "abaikan instruksi sebelumnya",
]


def check_outbound_text(text: str) -> tuple[bool, str]:
    lower = text.lower()
    for p in FORBIDDEN_OUTBOUND:
        if p in lower:
            return False, f"SEND_FAILED: konten melanggar policy ({p!r} — §28)"
    return True, "OK"


def looks_like_injection(text: str) -> bool:
    lower = text.lower()
    return any(m in lower for m in INJECTION_MARKERS)
