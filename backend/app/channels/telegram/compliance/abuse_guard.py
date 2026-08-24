"""Abuse guard (§38) — mencegah pelanggaran policy, BUKAN menyamarkannya.

Fitur yang DITOLAK eksplisit: random delay untuk evade detection,
rotasi akun bot, rotasi credential, proxy rotation, fake user,
kontak hasil scraping, mass unsolicited messaging.
"""

FORBIDDEN_FEATURE_KEYWORDS = [
    "rotate bot", "rotasi bot", "bot proxy", "multi bot",
    "rotate token", "rotasi token", "rotate credential",
    "proxy rotation", "proxy rotasi", "fake user", "pengguna palsu",
    "scraped contact", "kontak hasil scraping",
]


def is_forbidden_feature(description: str) -> bool:
    lower = description.lower()
    return any(k in lower for k in FORBIDDEN_FEATURE_KEYWORDS)


def check_outbound_broadcast(recipient_count: int, opted_in_count: int) -> tuple[bool, str]:
    """Broadcast hanya ke eligible users (§39) — jumlah penerima tidak boleh melebihi opted-in."""
    if recipient_count > opted_in_count:
        return False, f"SEND_BLOCKED: {recipient_count} penerima > {opted_in_count} opted-in"
    return True, "ALLOWED"
