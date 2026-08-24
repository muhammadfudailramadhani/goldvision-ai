"""Universal message policy (§37) — WAJIB sebelum setiap send.

Message -> Consent -> Preference -> Suppression -> Rate Limit -> Duplicate
        -> Channel Policy -> Queue -> Send -> Delivery Log.

Jika satu gagal: DO NOT SEND.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

BLOCK_REASONS = {
    "SEND_ALLOWED", "SEND_BLOCKED_NO_CONSENT", "SEND_BLOCKED_INACTIVE",
    "SEND_BLOCKED_OPT_OUT", "SEND_BLOCKED_SUPPRESSED", "SEND_BLOCKED_RATE_LIMIT",
    "SEND_BLOCKED_DUPLICATE", "SEND_BLOCKED_QUIET_HOURS", "SEND_BLOCKED_QUOTA",
    "SEND_BLOCKED_SUBSCRIPTION", "SEND_FAILED", "SEND_OK",
}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str  # salah satu dari BLOCK_REASONS
    detail: str = ""

    @property
    def code(self) -> str:
        return "SEND_ALLOWED" if self.allowed else self.reason


@dataclass
class PolicyDeps:
    """Dependency injection — channel menyuplai, core tidak query platform."""
    has_consent: bool = True
    is_active: bool = True
    notifications_enabled: bool = True
    is_suppressed: bool = False
    rate_limit_ok: bool = True
    is_duplicate: bool = False
    in_quiet_hours: bool = False
    channel_policy_ok: bool = True


def _in_quiet_hours(now_hour: int, start: int | None, end: int | None) -> bool:
    if start is None or end is None:
        return False
    if start <= end:
        return start <= now_hour < end
    return now_hour >= start or now_hour < end  # lintas tengah malam


class UniversalMessagePolicy:
    """Urutan check §37 — konsisten untuk Telegram sekarang dan WhatsApp nanti."""

    def evaluate(self, deps: PolicyDeps, now: datetime | None = None,
                 quiet_start: int | None = None, quiet_end: int | None = None) -> PolicyDecision:
        now = now or datetime.now(timezone.utc)

        if not deps.has_consent:
            return PolicyDecision(False, "SEND_BLOCKED_NO_CONSENT",
                                  "user belum pernah memulai chat (§20)")
        if not deps.is_active:
            return PolicyDecision(False, "SEND_BLOCKED_INACTIVE",
                                  "user blocked/inactive (§26)")
        if not deps.notifications_enabled:
            return PolicyDecision(False, "SEND_BLOCKED_OPT_OUT",
                                  "user menonaktifkan notifikasi (§21)")
        if deps.is_suppressed:
            return PolicyDecision(False, "SEND_BLOCKED_SUPPRESSED",
                                  "user di suppression list (§33)")
        if _in_quiet_hours(now.hour, quiet_start, quiet_end):
            return PolicyDecision(False, "SEND_BLOCKED_QUIET_HOURS",
                                  f"quiet hours {quiet_start}-{quiet_end} (§42)")
        if not deps.rate_limit_ok:
            return PolicyDecision(False, "SEND_BLOCKED_RATE_LIMIT",
                                  "rate limit terlampaui (§22)")
        if deps.is_duplicate:
            return PolicyDecision(False, "SEND_BLOCKED_DUPLICATE",
                                  "signal fingerprint identik (§25)")
        if not deps.channel_policy_ok:
            return PolicyDecision(False, "SEND_FAILED",
                                  "channel policy menolak (spam guard/abuse guard)")
        return PolicyDecision(True, "SEND_ALLOWED")
