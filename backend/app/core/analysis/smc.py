"""SMC (Smart Money Concepts) — versi terkalibrasi untuk foundation:

- Order Block: candle berlawanan terakhir sebelum gerak impulsif.
- FVG (Fair Value Gap): gap antara high[i-1] dan low[i+1] pada 3 candle.
- Bias arah dari kombinasi keduanya.

Deteksi lengkap (multi OB, mitigation, liquidity sweep) = FASE 2 —
ditandai eksplisit, bukan placeholder diam-diam.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SmcResult:
    bias: str  # BULLISH | BEARISH | NEUTRAL
    order_blocks: list  # list[dict(price_low, price_high, kind)]
    fvgs: list  # list[dict(low, high, kind)]
    note: str


def _atr(candles: list, period: int = 14) -> float:
    seg = candles[-period:]
    trs = [max(seg[i].high - seg[i].low,
               abs(seg[i].high - seg[i - 1].close),
               abs(seg[i].low - seg[i - 1].close))
           for i in range(1, len(seg))]
    return sum(trs) / max(len(trs), 1)


def detect_smc(candles: list) -> SmcResult:
    if len(candles) < 30:
        return SmcResult("NEUTRAL", [], [], "data tidak cukup")
    atr = _atr(candles)
    price = candles[-1].close
    obs, fvgs = [], []

    for i in range(len(candles) - 3, 2, -1):
        move = candles[i + 1].close - candles[i + 1].open
        if abs(move) < atr * 1.5:
            continue
        ob = candles[i]
        if move > 0 and ob.close < ob.open:  # candle turun sebelum naik impulsif = bullish OB
            obs.append({"low": round(ob.low, 5), "high": round(ob.high, 5), "kind": "BULLISH"})
        elif move < 0 and ob.close > ob.open:
            obs.append({"low": round(ob.low, 5), "high": round(ob.high, 5), "kind": "BEARISH"})
        if len(obs) >= 3:
            break

    for i in range(len(candles) - 2, len(candles) - 22, -1):
        prev, mid, nxt = candles[i - 2], candles[i - 1], candles[i]
        if nxt.low > prev.high:
            fvgs.append({"low": round(prev.high, 5), "high": round(nxt.low, 5), "kind": "BULLISH"})
        elif nxt.high < prev.low:
            fvgs.append({"low": round(nxt.high, 5), "high": round(prev.low, 5), "kind": "BEARISH"})
        if len(fvgs) >= 3:
            break

    near_ob = next((ob for ob in obs
                    if price >= ob["low"] * 0.999 and price <= ob["high"] * 1.001), None)
    bull = sum(1 for ob in obs if ob["kind"] == "BULLISH") + sum(1 for f in fvgs if f["kind"] == "BULLISH")
    bear = sum(1 for ob in obs if ob["kind"] == "BEARISH") + sum(1 for f in fvgs if f["kind"] == "BEARISH")

    if near_ob:
        bias = near_ob["kind"]
    else:
        bias = "BULLISH" if bull > bear else "BEARISH" if bear > bull else "NEUTRAL"
    note = f"{len(obs)} OB, {len(fvgs)} FVG; harga {'di dalam' if near_ob else 'di luar'} OB terdekat"
    return SmcResult(bias, obs, fvgs, note)
