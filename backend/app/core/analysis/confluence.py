"""Confluence (§14): multi-timeframe alignment + hitungan komponen searah.

Aturan keras: D1 dan H4 bertentangan kuat -> WAIT / NO TRADE.
"""
from dataclasses import dataclass

TF_ORDER = ["D1", "H4", "H1", "M30", "M15"]


@dataclass(frozen=True)
class ConfluenceResult:
    aligned: int
    conflicts: int
    tf_blocked: bool  # True = D1 vs H4 konflik kuat -> WAJIB WAIT (§14)
    reasons: list


def _polarity(direction: str) -> int:
    return {"BULLISH": 1, "BEARISH": -1}.get(direction, 0)


def analyze_confluence(trend_by_tf: dict[str, str]) -> ConfluenceResult:
    d1, h4 = _polarity(trend_by_tf.get("D1", "NEUTRAL")), _polarity(trend_by_tf.get("H4", "NEUTRAL"))
    strong_conflict = d1 * h4 == -1  # keduanya tegas dan berlawanan
    votes = [_polarity(trend_by_tf.get(tf, "NEUTRAL")) for tf in TF_ORDER]
    net = sum(votes)
    aligned = sum(1 for v in votes if v != 0 and v == (1 if net >= 0 else -1))
    conflicts = sum(1 for v in votes if v != 0 and v != (1 if net >= 0 else -1))

    reasons = [f"{tf}: {trend_by_tf.get(tf, 'NEUTRAL')}" for tf in TF_ORDER]
    if strong_conflict:
        reasons.insert(0, "D1 dan H4 bertentangan kuat — aturan §14: WAIT / NO TRADE")
    return ConfluenceResult(aligned, conflicts, strong_conflict, reasons)
