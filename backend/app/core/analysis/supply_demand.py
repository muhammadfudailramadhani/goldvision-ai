"""Supply/Demand: zone dari candle ber-body besar (inisiator gerak) yang belum tertutup penuh."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Zone:
    low: float
    high: float
    kind: str  # SUPPLY | DEMAND
    strength: float  # 0..1


def _atr(candles: list, period: int = 14) -> float:
    seg = candles[-period:]
    trs = [max(seg[i].high - seg[i].low,
               abs(seg[i].high - seg[i - 1].close),
               abs(seg[i].low - seg[i - 1].close))
           for i in range(1, len(seg))]
    return sum(trs) / max(len(trs), 1)


def find_zones(candles: list, body_mult: float = 1.6) -> list[Zone]:
    if len(candles) < 25:
        return []
    atr = _atr(candles)
    price = candles[-1].close
    zones: list[Zone] = []
    for i in range(len(candles) - 20, len(candles) - 2):
        c = candles[i]
        body = abs(c.close - c.open)
        if body < atr * body_mult:
            continue
        zone = Zone(
            low=round(min(c.open, c.close), 5),
            high=round(max(c.open, c.close), 5),
            kind="DEMAND" if c.close > c.open else "SUPPLY",
            strength=round(min(body / (atr * 3), 1.0), 2),
        )
        # abaikan zone yang sudah tertembus penuh oleh harga sekarang
        if zone.kind == "DEMAND" and price < zone.low:
            continue
        if zone.kind == "SUPPLY" and price > zone.high:
            continue
        if any(z.low == zone.low and z.high == zone.high for z in zones):
            continue
        zones.append(zone)
    return zones[-4:]
