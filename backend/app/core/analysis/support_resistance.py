"""Support/Resistance: klaster level pivot, relatif terhadap harga sekarang."""
from dataclasses import dataclass

from .market_structure import find_pivots


@dataclass(frozen=True)
class Level:
    price: float
    kind: str  # SUPPORT | RESISTANCE
    touches: int


def _cluster(prices: list[float], tol: float) -> list[list[float]]:
    groups: list[list[float]] = []
    for p in sorted(prices):
        if groups and abs(p - sum(groups[-1]) / len(groups[-1])) <= tol:
            groups[-1].append(p)
        else:
            groups.append([p])
    return groups


def find_levels(candles: list, tolerance_pct: float = 0.15) -> list[Level]:
    if len(candles) < 20:
        return []
    price = candles[-1].close
    span = max(c.high for c in candles) - min(c.low for c in candles)
    tol = max(span * tolerance_pct / 100, 1e-6)
    pivots = find_pivots(candles)
    levels: list[Level] = []
    for kind in ("HIGH", "LOW"):
        pts = [p.price for p in pivots if p.kind == kind]
        for group in _cluster(pts, tol):
            lvl = sum(group) / len(group)
            role = "RESISTANCE" if lvl > price else "SUPPORT"
            levels.append(Level(round(lvl, 5), role, len(group)))
    return sorted(levels, key=lambda l: abs(l.price - price))[:6]
