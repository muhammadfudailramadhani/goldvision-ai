"""Recommendation: susun rencana trade (entry/SL/TP) dari hasil analisis M15/M30.

Level SL/TP dihitung dari struktur (zone/pivot/ATR) — bukan angka bulat karangan.
"""
from dataclasses import dataclass

from .market_structure import analyze_structure
from .supply_demand import _atr, find_zones


@dataclass(frozen=True)
class Recommendation:
    action: str  # BUY | SELL | WAIT | NO_TRADE
    entry: float | None
    sl: float | None
    tp1: float | None
    tp2: float | None
    rr: float | None
    reasons: list


def build_recommendation(candles_m15: list, bias: str, score: int, tf_blocked: bool) -> Recommendation:
    price = candles_m15[-1].close
    atr = _atr(candles_m15)
    zones = find_zones(candles_m15)
    structure = analyze_structure(candles_m15)

    reasons: list[str] = []
    if tf_blocked:
        reasons.append("D1 vs H4 konflik kuat (§14)")
        return Recommendation("WAIT", None, None, None, None, None, reasons)
    if score < 40:
        reasons.append(f"score {score} < 40 (NO TRADE)")
        return Recommendation("NO_TRADE", None, None, None, None, None, reasons)
    if bias not in ("BULLISH", "BEARISH"):
        reasons.append("bias arah tidak tegas")
        return Recommendation("WAIT", None, None, None, None, None, reasons)
    if score < 60:
        reasons.append(f"score {score} di zona WEAK/MODERATE bawah — menunggu konfirmasi entry (M15)")

    demand = [z for z in zones if z.kind == "DEMAND"]
    supply = [z for z in zones if z.kind == "SUPPLY"]
    if bias == "BULLISH":
        entry = demand[0].high if demand else price
        sl = round(min(entry - 1.5 * atr, demand[0].low - 0.2 * atr if demand else entry - 1.5 * atr), 5)
        tp1, tp2 = round(entry + 1.5 * atr, 5), round(entry + 3.0 * atr, 5)
    else:
        entry = supply[0].low if supply else price
        sl = round(max(entry + 1.5 * atr, supply[0].high + 0.2 * atr if supply else entry + 1.5 * atr), 5)
        tp1, tp2 = round(entry - 1.5 * atr, 5), round(entry - 3.0 * atr, 5)

    risk = abs(entry - sl)
    reward = abs(tp2 - entry)
    rr = round(reward / risk, 2) if risk > 0 else None
    reasons.append(f"struktur {structure.structure}; entry dari zone {'demand' if bias == 'BULLISH' else 'supply'}")
    action = "BUY" if bias == "BULLISH" else "SELL"
    return Recommendation(action, round(entry, 5), sl, tp1, tp2, rr, reasons)
