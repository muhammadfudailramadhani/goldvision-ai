"""Trend: arah & kekuatan via SMA slope + urutan swing."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TrendResult:
    direction: str  # BULLISH | BEARISH | NEUTRAL
    strength: float  # 0..1
    note: str


def _sma(values: list[float], period: int) -> float:
    window = values[-period:]
    return sum(window) / len(window)


def detect_trend(closes: list[float]) -> TrendResult:
    if len(closes) < 50:
        return TrendResult("NEUTRAL", 0.0, "data tidak cukup")
    sma20, sma50 = _sma(closes, 20), _sma(closes, 50)
    slope = (closes[-1] - closes[-10]) / max(closes[-10], 1e-9)  # momentum 10 candle
    sep = (sma20 - sma50) / max(sma50, 1e-9)  # pemisahan MA

    if sma20 > sma50 and slope > 0:
        strength = min(abs(sep) * 40 + abs(slope) * 20, 1.0)
        return TrendResult("BULLISH", round(strength, 2), "SMA20>SMA50, momentum naik")
    if sma20 < sma50 and slope < 0:
        strength = min(abs(sep) * 40 + abs(slope) * 20, 1.0)
        return TrendResult("BEARISH", round(strength, 2), "SMA20<SMA50, momentum turun")
    return TrendResult("NEUTRAL", 0.2, "MA menyilang / datar")
