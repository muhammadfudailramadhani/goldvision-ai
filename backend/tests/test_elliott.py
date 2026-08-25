"""Test Elliott Wave rule-based (FASE 2) — aturan keras R1/R2/R3 + guideline confidence."""
import pytest

from app.core.analysis.elliott_wave import (_guideline_confidence, _passes_hard_rules,
                                            _waves_from_pivots, detect_elliott)
from app.core.analysis.market_structure import Pivot


def _pivots(*specs):
    """specs: (index, 'HIGH'|'LOW', price) -> list[Pivot]"""
    return [Pivot(i, p, k) for i, k, p in specs]


def _impulse_up_pivots():
    """Impulse UP ideal: w2 retrace 70% w1, w4 retrace 40% w3, w3 terpanjang.
    L100 H110 L103 H130 L118 H135 -> conf guideline = 0.35+0.35+0.30 = 1.00"""
    return _pivots((2, "LOW", 100), (6, "HIGH", 110), (10, "LOW", 103),
                   (14, "HIGH", 130), (18, "LOW", 118), (22, "HIGH", 135))


# ---------------------------------------------------------------- unit aturan

def test_waves_from_alternating_pivots():
    waves = _waves_from_pivots(_impulse_up_pivots(), 0)
    assert waves is not None and len(waves) == 5
    assert [w.label for w in waves] == ["1", "2", "3", "4", "5"]
    assert all(w.direction == "UP" for w in (waves[0], waves[2], waves[4]))
    assert all(w.direction == "DOWN" for w in (waves[1], waves[3]))


def test_non_alternating_pivots_rejected():
    pivots = _pivots((2, "LOW", 100), (6, "LOW", 90), (10, "HIGH", 110),
                     (14, "LOW", 103), (18, "HIGH", 130), (22, "LOW", 118))
    assert _waves_from_pivots(pivots, 0) is None


def test_hard_rules_pass_ideal_impulse():
    waves = _waves_from_pivots(_impulse_up_pivots(), 0)
    assert _passes_hard_rules(waves) is True
    assert _guideline_confidence(waves) == pytest.approx(1.0)


def test_r1_wave2_penetrates_wave1_start_rejected():
    pivots = _pivots((2, "LOW", 100), (6, "HIGH", 110), (10, "LOW", 95),
                     (14, "HIGH", 130), (18, "LOW", 118), (22, "HIGH", 135))
    waves = _waves_from_pivots(pivots, 0)
    assert _passes_hard_rules(waves) is False  # w2.end 95 < w1.start 100


def test_r2_wave3_shortest_rejected():
    pivots = _pivots((2, "LOW", 100), (6, "HIGH", 130), (10, "LOW", 120),
                     (14, "HIGH", 125), (18, "LOW", 115), (22, "HIGH", 160))
    waves = _waves_from_pivots(pivots, 0)
    # w3=5 lebih pendek dari w1=30 & w5=45 -> melanggar R2
    assert _passes_hard_rules(waves) is False


def test_r3_wave4_overlaps_wave1_territory_rejected():
    pivots = _pivots((2, "LOW", 100), (6, "HIGH", 110), (10, "LOW", 103),
                     (14, "HIGH", 130), (18, "LOW", 108), (22, "HIGH", 135))
    waves = _waves_from_pivots(pivots, 0)
    assert _passes_hard_rules(waves) is False  # w4.end 108 < w1.end 110


def test_guideline_confidence_partial():
    # w2 retrace 50% (ok), w4 retrace 80% (di luar 23.6-61.8), w3 terpanjang
    pivots = _pivots((2, "LOW", 100), (6, "HIGH", 110), (10, "LOW", 105),
                     (14, "HIGH", 130), (18, "LOW", 114), (22, "HIGH", 128))
    waves = _waves_from_pivots(pivots, 0)
    assert _guideline_confidence(waves) == pytest.approx(0.65)


# ---------------------------------------------------------------- integrasi

def _candles_from_zigzag(pivots):
    """Candle sintetis yang pivot-nya PERSIS di titik yang ditentukan.

    close piecewise-linear antar pivot; high/low dipadatkan supaya hanya
    titik pivot yang jadi ekstrem window-nya (window=2).
    Terima list[Pivot] atau tuple (index, kind, price).
    """
    from app.core.analysis.market_structure import Pivot

    pivots = [p if isinstance(p, Pivot) else Pivot(p[0], p[2], p[1]) for p in pivots]
    n = pivots[-1].index + 3
    # lead-in/out MIRING menjauh dari pivot ujung supaya pivot terdeteksi
    # (padding flat akan menimpa ekstrem pivot pertama/terakhir)
    first, last = pivots[0], pivots[-1]
    lead = first.price + 5 if first.kind == "LOW" else first.price - 5
    tail = last.price - 5 if last.kind == "HIGH" else last.price + 5
    pts = [(0, lead), (first.index, first.price)] + \
          [(p.index, p.price) for p in pivots[1:]] + [(n - 1, tail)]

    def close_at(i):
        for (a, pa), (b, pb) in zip(pts, pts[1:]):
            if a <= i <= b:
                if a == b:
                    return pa
                return pa + (pb - pa) * (i - a) / (b - a)
        return pts[-1][1]

    candles = []
    pivot_by_idx = {p.index: (p.kind, p.price) for p in pivots}
    for i in range(n):
        c = round(close_at(i), 5)
        kind_price = pivot_by_idx.get(i)
        if kind_price and kind_price[0] == "HIGH":
            hi, lo = float(kind_price[1]), round(c - 0.6, 5)
        elif kind_price and kind_price[0] == "LOW":
            hi, lo = round(c + 0.6, 5), float(kind_price[1])
        else:
            hi, lo = round(c + 0.3, 5), round(c - 0.3, 5)
        candles.append(Candle(ts=i * 900, open=c, high=hi, low=min(lo, c),
                              close=c, volume=1000))
    return candles


from app.core.market.provider import Candle  # noqa: E402


def test_detect_impulse_up_on_synthetic_zigzag():
    result = detect_elliott(_candles_from_zigzag(_impulse_up_pivots()))
    assert result.status == "DETECTED"
    assert result.pattern == "IMPULSE_UP"
    assert result.current_wave == "5"
    assert result.confidence > 0.5
    assert len(result.waves) == 5


def test_detect_all_windows_violate_r1_unclear():
    # staircase turun: setiap trough lebih dalam dari start wave-1 kandidat mana pun
    pivots = _pivots((2, "LOW", 100), (6, "HIGH", 108), (10, "LOW", 96),
                     (14, "HIGH", 104), (18, "LOW", 92), (22, "HIGH", 100))
    result = detect_elliott(_candles_from_zigzag(pivots))
    assert result.status == "UNCLEAR"


def test_detect_not_enough_data_short_series():
    short = _candles_from_zigzag([(2, "LOW", 100), (6, "HIGH", 110), (10, "LOW", 103)])
    assert detect_elliott(short).status == "NOT_ENOUGH_DATA"
