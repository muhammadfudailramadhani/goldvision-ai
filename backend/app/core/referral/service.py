"""ReferralService (§19 / docs/19-referral.md) — FASE 2.

Kontrak:
- Setiap user boleh punya tepat satu referral_code (unique, pendek, stabil).
- Pemakai kode dicatat sebagai referred_by pada user baru; hanya boleh sekali.
- Reward = tambahan quota live analysis (bonus_quota), BUKAN akses VIP gratis.
- Anti-abuse: self-referral ditolak, kode hanya bisa dipakai sekali per user,
  reward hanya diberikan setelah user yang direfer melakukan minimal
  1 live analysis (anti-farming akun kosong).
"""
import secrets
from dataclasses import dataclass

from sqlalchemy import select

from app.models import QuotaUsage, User
from app.repositories import QuotaRepo, UserRepo

REWARD_BONUS = 2          # tambahan live analysis per referral sukses
MIN_ACTIVITY_FOR_REWARD = 1  # referred user harus sudah analyze sekali


@dataclass(frozen=True)
class ReferralResult:
    ok: bool
    reason: str
    referrer_code: str | None = None


def generate_code() -> str:
    """Kode 8 karakter base32 (tanpa karakter ambigu 0/O/1/I)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


class ReferralService:
    def __init__(self, session):
        self.session = session
        self.users = UserRepo(session)
        self.quota = QuotaRepo(session)

    # --- kode milik user ---

    def ensure_code(self, user: User) -> str:
        """Idempotent: kembalikan kode yang sudah ada, buat baru jika belum."""
        if user.referral_code:
            return user.referral_code
        code = generate_code()
        # collision sangat jarang (32^8), tapi cek tetap wajib — unique constraint DB
        while self._code_owner(code) is not None:
            code = generate_code()
        user.referral_code = code
        self.session.flush()
        self.session.commit()
        return code

    def _code_owner(self, code: str) -> User | None:
        return self.session.scalar(select(User).where(User.referral_code == code))

    def stats(self, user: User) -> dict:
        referred = list(self.session.scalars(
            select(User).where(User.referred_by == user.id)))
        rewarded = [u for u in referred if u.referral_rewarded]
        return {
            "code": user.referral_code,
            "total_referred": len(referred),
            "rewarded": len(rewarded),
            "bonus_quota": user.bonus_quota,
        }

    # --- pemakaian kode ---

    def apply_code(self, user: User, code: str) -> ReferralResult:
        """Tempel kode referrer pada user (sekali seumur hidup user)."""
        code = (code or "").strip().upper()
        if not code:
            return ReferralResult(False, "Kode referral kosong.")
        if user.referred_by is not None:
            return ReferralResult(False, "Kamu sudah memakai kode referral sebelumnya.")
        owner = self._code_owner(code)
        if owner is None:
            return ReferralResult(False, f"Kode {code} tidak ditemukan.")
        if owner.id == user.id:
            return ReferralResult(False, "Self-referral tidak diizinkan (§19 anti-abuse).")
        user.referred_by = owner.id
        self.session.flush()
        self.session.commit()
        return ReferralResult(True, f"Berhasil! Kamu direferensikan oleh {code}.",
                              referrer_code=code)

    # --- reward ---

    def maybe_grant_reward(self, referred_user: User) -> ReferralResult:
        """Panggil setelah referred_user mengonsumsi live analysis.

        Beri bonus ke referrer sekali saja, hanya jika referred user sudah
        aktif (>= MIN_ACTIVITY_FOR_REWARD analysis). Idempotent.
        """
        if referred_user.referred_by is None or referred_user.referral_rewarded:
            return ReferralResult(False, "Tidak ada reward yang jatuh tempo.")
        used = self.quota.count_since(referred_user.id, referred_user.created_at)
        if used < MIN_ACTIVITY_FOR_REWARD:
            return ReferralResult(False, "Referred user belum aktif — reward ditahan (anti-farming).")
        referrer = self.users.get(referred_user.referred_by)
        if referrer is None:
            return ReferralResult(False, "Referrer tidak ditemukan.")
        referrer.bonus_quota += REWARD_BONUS
        referred_user.referral_rewarded = True
        self.session.flush()
        self.session.commit()
        return ReferralResult(True, f"Reward +{REWARD_BONUS} analysis untuk {referrer.referral_code}.",
                              referrer_code=referrer.referral_code)
