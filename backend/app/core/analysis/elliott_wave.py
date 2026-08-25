"""Elliott Wave — FASE 2 implementasi berbasis aturan (rule-based), bukan AI tebakan.

Metode: deteksi swing pivot -> cari kandidat impulse 5-gelombang (uptrend maupun
downtrend) yang lolos TIGA aturan keras Elliott:
  R1: Wave 2 tidak pernah menembus awal Wave 1.
  R2: Wave 3 tidak pernah gelombang terpendek di antara 1, 3, 5.
  R3: Wave 4 tidak overlap territory Wave 1 (kecuali diagonal, tidak dipakai di sini).
Guideline tambahan (dipakai sebagai skor keyakinan, bukan syarat mutlak):
  G1: retracement Wave 2 = 38.2%-78.6% panjang Wave 1.
  G2: retracement Wave 4 = 23.6%-61.8% panjang Wave 3.
Kalau tidak ada kandidat yang lolos: status UNCLEAR — jangan mengarang count.
"""
from dataclasses import dataclass, field

from .market_structure import Pivot, find_pivots

STATUS = {
    "DETECTED": "impulse 5-gelombang terdeteksi dan lolos aturan keras",
    "UNCLEAR": "tidak ada pola 5-gelombang yang lolos aturan — jangan mengarang count",
    "NOT_ENOUGH_DATA": "pivot kurang dari 6 — data terlalu pendek untuk Elliott",
}


@dataclass(frozen=True)
class Wave:
    label: str  # "1".."5"
    start_index: int
    end_index: int
    start_price: float
    end_price: float

    @property
    def length(self) -> float:
        return abs(self.end_price - self.start_price)

    @property
    def direction(self) -> str:
        return "UP" if self.end_price > self.start_price else "DOWN"


@dataclass(frozen=True)
class ElliottResult:
    status: str  # DETECTED | UNCLEAR | NOT_ENOUGH_DATA
    note: str
    pattern: str | None = None   # IMPULSE_UP | IMPULSE_DOWN
    waves: list = field(default_factory=list)
    current_wave: str | None = None  # label gelombang terakhir yang terbentuk
    confidence: float = 0.0  # 0..1 dari guideline retracement


def _waves_from_pivots(pivots: list[Pivot], start: int) -> list[Wave] | None:
    """Bangun 5 gelombang dari 6 pivot berurutan (alternating HIGH/LOW)."""
    seq = pivots[start : start + 6]
    if len(seq) < 6:
        return None
    # pivot harus alternating; kalau ada dua HIGH/LOW berurutan, bukan struktur wave
    for a, b in zip(seq, seq[1:]):
        if a.kind == b.kind:
            return None
    labels = ["1", "2", "3", "4", "5"]
    return [
        Wave(labels[i], seq[i].index, seq[i + 1].index, seq[i].price, seq[i + 1].price)
        for i in range(5)
    ]


def _passes_hard_rules(waves: list[Wave]) -> bool:
    w1, w2, w3, w4, w5 = waves
    # struktur impulse: wave 1,3,5 searah; wave 2,4 melawan
    if not (w1.direction == w3.direction == w5.direction):
        return False
    if w2.direction == w1.direction or w4.direction == w3.direction:
        return False
    # R1: wave 2 tidak menembus awal wave 1
    if w1.direction == "UP" and w2.end_price < w1.start_price:
        return False
    if w1.direction == "DOWN" and w2.end_price > w1.start_price:
        return False
    # R2: wave 3 bukan yang terpendek (dibanding wave 1 dan 5)
    if w3.length <= w1.length and w3.length <= w5.length:
        return False
    # R3: wave 4 tidak overlap territory wave 1
    if w1.direction == "UP" and w4.end_price < w1.end_price:
        return False
    if w1.direction == "DOWN" and w4.end_price > w1.end_price:
        return False
    return True


def _guideline_confidence(waves: list[Wave]) -> float:
    """Skor 0..1 dari guideline retracement (bukan syarat mutlak)."""
    w1, w2, w3, w4, w5 = waves
    conf = 0.0
    r2 = w2.length / w1.length if w1.length else 0.0
    if 0.382 <= r2 <= 0.786:
        conf += 0.35
    r4 = w4.length / w3.length if w3.length else 0.0
    if 0.236 <= r4 <= 0.618:
        conf += 0.35
    # wave 3 extension (umumnya terpanjang)
    if w3.length > w1.length and w3.length > w5.length:
        conf += 0.3
    return round(min(conf, 1.0), 2)


def detect_elliott(candles: list, window: int = 2) -> ElliottResult:
    if len(candles) < window * 2 + 6:
        return ElliottResult("NOT_ENOUGH_DATA", STATUS["NOT_ENOUGH_DATA"])

    pivots = find_pivots(candles, window=window)
    if len(pivots) < 6:
        return ElliottResult("NOT_ENOUGH_DATA", STATUS["NOT_ENOUGH_DATA"])

    best: tuple[float, list[Wave]] | None = None
    for start in range(len(pivots) - 5):
        waves = _waves_from_pivots(pivots, start)
        if waves is None or not _passes_hard_rules(waves):
            continue
        conf = _guideline_confidence(waves)
        if best is None or conf > best[0]:
            best = (conf, waves)

    if best is None:
        return ElliottResult("UNCLEAR", STATUS["UNCLEAR"])

    conf, waves = best
    pattern = "IMPULSE_UP" if waves[0].direction == "UP" else "IMPULSE_DOWN"
    return ElliottResult(
        status="DETECTED",
        note=f"{pattern}: 5 gelombang lolos aturan keras (R1/R2/R3), keyakinan guideline {conf:.0%}",
        pattern=pattern,
        waves=waves,
        current_wave="5",
        confidence=conf,
    )
