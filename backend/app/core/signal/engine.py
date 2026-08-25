"""SignalEngine (§17, §25, §41): analysis -> sinyal atau tidak.

Frequency control: score threshold, min confluence, min RR, cooldown,
duplicate protection via fingerprint. Tidak menghasilkan sinyal demi
mengirim pesan.
"""
import hashlib
from dataclasses import dataclass

SCORE_THRESHOLD = 60
MIN_CONFLUENCE = 3
MIN_RR = 1.5
SIGNAL_VERSION = "v1"
COOLDOWN_MINUTES = 240  # same-direction cooldown default


@dataclass(frozen=True)
class SignalCandidate:
    pair: str
    direction: str
    timeframe: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    score: int
    fingerprint: str


def make_fingerprint(pair: str, direction: str, entry: float, sl: float,
                     tp1: float, tp2: float, timeframe: str) -> str:
    """§25: hash komponen sinyal — fingerprint sama = DO NOT SEND DUPLICATE."""
    payload = f"{pair}|{direction}|{round(entry, 2)}|{round(sl, 2)}|{round(tp1, 2)}|{round(tp2, 2)}|{timeframe}|{SIGNAL_VERSION}"
    return hashlib.sha256(payload.encode()).hexdigest()


def evaluate_for_signal(analysis) -> SignalCandidate | None:
    rec = analysis.recommendation
    if rec.action not in ("BUY", "SELL"):
        return None
    if analysis.score.total < SCORE_THRESHOLD:
        return None
    if analysis.confluence.aligned < MIN_CONFLUENCE:
        return None
    if rec.rr is not None and rec.rr < MIN_RR:
        return None
    fp = make_fingerprint(analysis.pair, rec.action, rec.entry, rec.sl, rec.tp1, rec.tp2,
                          getattr(analysis, "chart_timeframe", None) or "M15")
    return SignalCandidate(
        pair=analysis.pair, direction=rec.action, timeframe="M15",
        entry=rec.entry, sl=rec.sl, tp1=rec.tp1, tp2=rec.tp2,
        score=analysis.score.total, fingerprint=fp,
    )


def is_duplicate(fingerprint: str, known_fingerprints: set[str]) -> bool:
    return fingerprint in known_fingerprints
