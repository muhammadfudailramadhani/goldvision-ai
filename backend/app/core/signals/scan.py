"""Signal scanner (FASE 2+) — scan pair -> SignalEngine -> dedup fingerprint -> simpan.

Dipakai /admin_scan (manual) dan scripts/auto_signal.py (scheduler loop).
Tidak pernah mengarang sinyal: hanya lolos filter SignalEngine yang tersimpan.
"""
from datetime import datetime, timezone

from app.core.analysis.engine import AnalysisEngine
from app.core.market.provider import PAIRS
from app.core.signal.engine import COOLDOWN_MINUTES, evaluate_for_signal
from app.repositories import SignalRepo


def _in_cooldown(repo: SignalRepo, pair: str, direction: str) -> bool:
    return len(repo.recent_for_pair(pair, direction,
                                    within_minutes=COOLDOWN_MINUTES)) > 0


async def scan_pairs(provider, session, pairs: list[str] | None = None,
                     timeframe: str = "M15") -> list:
    """Scan pair -> sinyal BARU tersimpan. Return daftar Signal baru (bisa kosong)."""
    engine = AnalysisEngine(provider)
    repo = SignalRepo(session)
    created = []
    for pair in (pairs or PAIRS):
        try:
            analysis = await engine.analyze(pair)
        except Exception:
            continue  # satu pair gagal (429 dsb) = skip pair itu, lanjut
        candidate = evaluate_for_signal(analysis)
        if candidate is None:
            continue
        if repo.fingerprint_exists(candidate.fingerprint):
            continue  # §25 dedup
        if _in_cooldown(repo, pair, candidate.direction):
            continue
        signal = repo.save(
            pair=pair, direction=candidate.direction, timeframe=candidate.timeframe,
            entry=candidate.entry, sl=candidate.sl, tp1=candidate.tp1,
            tp2=candidate.tp2, score=candidate.score,
            fingerprint=candidate.fingerprint,
        )
        signal.created_at = datetime.now(timezone.utc)
        created.append(signal)
    session.commit()
    return created
