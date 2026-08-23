"""Market structure: swing pivot, HH/HL/LH/LL, BOS/CHoCH."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Pivot:
    index: int
    price: float
    kind: str  # HIGH | LOW


@dataclass(frozen=True)
class StructureResult:
    structure: str  # UPTREND | DOWNTREND | RANGE
    pivots: list
    last_event: str | None  # BOS | CHoCH | None
    note: str


def find_pivots(candles: list, window: int = 2) -> list[Pivot]:
    pivots: list[Pivot] = []
    for i in range(window, len(candles) - window):
        seg = candles[i - window : i + window + 1]
        if candles[i].high == max(c.high for c in seg):
            pivots.append(Pivot(i, candles[i].high, "HIGH"))
        elif candles[i].low == min(c.low for c in seg):
            pivots.append(Pivot(i, candles[i].low, "LOW"))
    return pivots


def analyze_structure(candles: list) -> StructureResult:
    pivots = find_pivots(candles)
    if len(pivots) < 4:
        return StructureResult("RANGE", pivots, None, "pivot kurang (data terlalu pendek)")

    highs = [p for p in pivots if p.kind == "HIGH"]
    lows = [p for p in pivots if p.kind == "LOW"]
    hh = highs[-1].price > highs[-2].price
    hl = lows[-1].price > lows[-2].price
    lh = highs[-1].price < highs[-2].price
    ll = lows[-1].price < lows[-2].price

    if hh and hl:
        structure, event = "UPTREND", "BOS"
    elif lh and ll:
        structure, event = "DOWNTREND", "BOS"
    elif (hh and ll) or (lh and hl):
        structure, event = "RANGE", "CHoCH"
    else:
        return StructureResult("RANGE", pivots, None, "pola pivot campuran")

    note = ("higher highs & higher lows" if structure == "UPTREND"
            else "lower highs & lower lows" if structure == "DOWNTREND"
            else "ekspansi/pecah struktur dua arah")
    return StructureResult(structure, pivots, event, note)
