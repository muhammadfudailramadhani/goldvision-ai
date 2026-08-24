"""Spam guard (§28) — cek teks keluaran, bukan cek input.

Jangan biarkan bot mengirim: fake profit claim, misleading claim,
janjikan profit pasti, impersonasi Telegram, minta OTP/password.
"""

SPAM_PATTERNS = [
    "guaranteed profit", "pasti untung", "pasti profit", "100% win",
    "janji profit", "jaminan untung", "no loss ever", "zero risk",
    "masukkan password", "kirim OTP", "verifikasi via chat ini",
]


def is_spammy_text(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in SPAM_PATTERNS)
