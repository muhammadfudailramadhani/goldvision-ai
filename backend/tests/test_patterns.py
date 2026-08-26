"""Test chart pattern detection - data sintetis yang BENAR-BENAR berbentuk pola.

Prinsip: deteksi & gambar wajib sesuai data riil. Garis yang dilaporkan
harus melewati pivot asli (slope datar benar-benar datar, menanjak benar
menanjak) - bukan garis karangan.
"""
import pytest

from app.core.analysis.market_structure import find_pivots
from app.core.analysis.patterns import detect_patterns
from app.core.chart.generator import render_chart
from app.core.market.provider import Candle


def _candles_from_pivots(pivots, tail_close=None):
    """Bangun candle yang pivot-nya PERSIS di harga yang ditentukan."""
    n = pivots[-1][0] + 6
    first_i, first_kind, first_price = pivots[0]
    lead = first_price + 5 if first_kind == "LOW" else first_price - 5
    pts = [(0, lead), (first_i, first_price)] + \
        [(i, pr) for i, _, pr in pivots[1:]] + \
        [(n - 1, tail_close if tail_close is not None else pivots[-1][2])]

    def close_at(i):
        for (a, pa), (b, pb) in zip(pts, pts[1:]):
            if a <= i <= b:
                if a == b:
                    return pa
                return pa + (pb - pa) * (i - a) / (b - a)
        return pts[-1][1]

    pivot_by_idx = {i: (k, pr) for i, k, pr in pivots}
    candles = []
    for i in range(n):
        c = round(close_at(i), 5)
        kp = pivot_by_idx.get(i)
        if kp and kp[0] == "HIGH":
            hi, lo = float(kp[1]), round(c - 0.6, 5)
        elif kp and kp[0] == "LOW":
            hi, lo = round(c + 0.6, 5), float(kp[1])
        else:
            hi, lo = round(c + 0.3, 5), round(c - 0.3, 5)
        candles.append(Candle(ts=i * 900, open=c, high=hi,
                              low=min(lo, c), close=c, volume=1000))
    return candles


# ------------------------------------------------------------- segitiga naik

ASC_TRIANGLE = [
    (2, "LOW", 100.0), (6, "HIGH", 110.0),
    (12, "LOW", 103.5), (17, "HIGH", 110.0),
    (24, "LOW", 106.4), (30, "HIGH", 110.0),
    (38, "LOW", 107.4), (44, "HIGH", 109.9),
]


def test_ascending_triangle_lines_match_real_pivots():
    candles = _candles_from_pivots(ASC_TRIANGLE, tail_close=109.5)
    # pivot riil harus benar-benar flat di ~110 sebelum dideteksi
    real_highs = [p.price for p in find_pivots(candles, window=2) if p.kind == "HIGH"]
    assert real_highs and all(abs(h - 110) < 1.0 for h in real_highs), real_highs

    pats = detect_patterns(candles)
    match = next((p for p in pats if p.name == "ASCENDING_TRIANGLE"), None)
    assert match is not None, [p.name for p in pats]
    assert match.direction == "BULLISH"
    # GARIS SESUAI DATA: resistensi datar karena pivot aslinya memang datar
    hi_line = match.lines[0]
    assert abs(hi_line.slope) < 0.03, f"slope={hi_line.slope}"
    lo_line = match.lines[1]
    assert lo_line.slope > 0.05
    assert match.apex_x is not None and match.apex_x > len(candles)
    assert match.confidence >= 0.5
    assert len(match.points) >= 4


def test_descending_triangle_detected():
    pivots = [
        (2, "HIGH", 120.0), (7, "LOW", 100.0),
        (13, "HIGH", 112.5), (19, "LOW", 100.2),
        (26, "HIGH", 106.8), (33, "LOW", 99.9),
        (40, "HIGH", 103.4),
    ]
    candles = _candles_from_pivots(pivots, tail_close=101.0)
    pats = detect_patterns(candles)
    match = next((p for p in pats if p.name == "DESCENDING_TRIANGLE"), None)
    assert match is not None, [p.name for p in pats]
    assert match.direction == "BEARISH"
    assert abs(match.lines[1].slope) < 0.03   # support datar (pivot asli 100.x)
    assert match.lines[0].slope < -0.05       # resistensi turun


# ------------------------------------------------------------- reversal

def test_double_top_detected():
    pivots = [
        (2, "LOW", 112.0), (6, "HIGH", 124.0),
        (14, "LOW", 116.0), (22, "HIGH", 123.6),
        (30, "LOW", 113.0),
    ]
    candles = _candles_from_pivots(pivots, tail_close=115.0)
    pats = detect_patterns(candles)
    match = next((p for p in pats if p.name == "DOUBLE_TOP"), None)
    assert match is not None, [p.name for p in pats]
    assert match.direction == "BEARISH"
    # dua puncak riil selevel
    peaks = [pr for _, pr, k in match.points if k == "HIGH"]
    assert abs(peaks[0] - peaks[1]) <= 0.5
    assert match.confidence >= 0.6


def test_double_bottom_detected():
    pivots = [
        (2, "HIGH", 116.0), (12, "LOW", 100.0),
        (26, "HIGH", 108.0), (40, "LOW", 99.5),
        (52, "HIGH", 114.0),
    ]
    candles = _candles_from_pivots(pivots, tail_close=110.0)
    pats = detect_patterns(candles)
    match = next((p for p in pats if p.name == "DOUBLE_BOTTOM"), None)
    assert match is not None, [p.name for p in pats]
    assert match.direction == "BULLISH"


# ------------------------------------------------------------- guard & integrasi

def test_short_data_returns_empty():
    candles = _candles_from_pivots([(2, "LOW", 100.0), (6, "HIGH", 110.0)])
    assert detect_patterns(candles) == []


def test_no_pattern_in_clean_trend():
    # tren naik lurus tanpa struktur segitiga: tidak boleh dipaksa jadi pola
    candles = [Candle(ts=i * 900, open=100 + i * 0.8, high=101 + i * 0.8,
                      low=99 + i * 0.8, close=100.5 + i * 0.8, volume=10)
               for i in range(80)]
    pats = detect_patterns(candles)
    names = {p.name for p in pats}
    assert not names & {"ASCENDING_TRIANGLE", "SYMMETRICAL_TRIANGLE",
                        "DOUBLE_TOP", "DOUBLE_BOTTOM"}, names


@pytest.mark.asyncio
async def test_chart_renders_pattern_overlay(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    candles = _candles_from_pivots(ASC_TRIANGLE, tail_close=109.5)
    patterns = detect_patterns(candles)
    assert patterns, "data uji harus menghasilkan minimal satu pola"
    path = render_chart(pair="XAUUSD", timeframe="M15", candles=candles,
                        patterns=patterns)
    assert path.exists() and path.stat().st_size > 20_000  # PNG berisi overlay


def test_max_two_patterns_and_unique_names():
    from app.core.analysis.patterns import MAX_PATTERNS

    candles = _candles_from_pivots(ASC_TRIANGLE, tail_close=109.5)
    pats = detect_patterns(candles)
    assert len(pats) <= MAX_PATTERNS
    assert len({p.name for p in pats}) == len(pats)
