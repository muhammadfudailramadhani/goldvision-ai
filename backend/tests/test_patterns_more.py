"""Test pola tambahan: rectangle, triple top, flag, pennant, cup & handle."""
import pytest

from app.core.analysis import patterns as P
from app.core.analysis.patterns import detect_patterns
from test_patterns import _candles_from_pivots


def _atr_of(candles):
    return P._atr(candles)


# ---------------------------------------------------------------- rectangle

def test_rectangle_detected_via_detect_patterns():
    pivots = [
        (2, "LOW", 100.0), (8, "HIGH", 110.0),
        (14, "LOW", 100.2), (20, "HIGH", 109.8),
        (26, "LOW", 99.9), (32, "HIGH", 110.1),
    ]
    candles = _candles_from_pivots(pivots, tail_close=105.0)
    names = [p.name for p in detect_patterns(candles)]
    assert "RECTANGLE" in names, names


# ---------------------------------------------------------------- triple top

def test_triple_top_direct():
    pivots = [
        (2, "LOW", 104.0), (10, "HIGH", 110.0),
        (17, "LOW", 103.0), (24, "HIGH", 109.8),
        (31, "LOW", 103.2), (38, "HIGH", 110.1),
    ]
    candles = _candles_from_pivots(pivots, tail_close=107.0)
    m = P._triple_pattern(candles, _atr_of(candles))
    assert m is not None and m.name == "TRIPLE_TOP"
    assert m.direction == "BEARISH"
    assert len([p for p in m.points if p[2] == "HIGH"]) == 3


# ---------------------------------------------------------------- flag & pennant

FLAG_BULL = [
    (4, "LOW", 100.0), (12, "HIGH", 112.0),
    (18, "HIGH", 111.6), (22, "LOW", 110.4),
    (27, "HIGH", 111.2), (32, "LOW", 110.1),
    (37, "HIGH", 111.0),
]
PENNANT_BULL = [
    (4, "LOW", 100.0), (12, "HIGH", 112.0),
    (18, "HIGH", 111.8), (22, "LOW", 110.2),
    (27, "HIGH", 111.2), (32, "LOW", 110.6),
    (37, "HIGH", 110.8),
]


def test_bull_flag_detected_with_pole_line():
    candles = _candles_from_pivots(FLAG_BULL, tail_close=110.8)
    m = P._flag_pennant_pattern(candles, _atr_of(candles))
    assert m is not None, "flag harus terdeteksi"
    assert m.name == "BULL_FLAG" and m.direction == "BULLISH"
    # garis tiang = gerakan riil 100 -> 112
    pole = m.lines[0]
    assert pole.y1 - pole.y0 > 8
    assert len(m.lines) == 3  # tiang + 2 garis bendera


def test_pennant_detected_converging():
    candles = _candles_from_pivots(PENNANT_BULL, tail_close=110.6)
    m = P._flag_pennant_pattern(candles, _atr_of(candles))
    assert m is not None and m.name == "PENNANT"
    assert m.apex_x is not None and m.apex_x > len(candles)


# ---------------------------------------------------------------- cup & handle

CUP_HANDLE = [
    (2, "HIGH", 108.0), (10, "LOW", 102.0),
    (18, "HIGH", 107.5), (30, "LOW", 94.5),
    (42, "HIGH", 107.0), (54, "LOW", 101.8),
    (64, "HIGH", 104.0), (72, "LOW", 102.6),
    (80, "HIGH", 105.5),
]


def test_cup_and_handle_with_curve_through_real_lows():
    candles = _candles_from_pivots(CUP_HANDLE, tail_close=104.8)
    m = P._cup_handle_pattern(candles, _atr_of(candles))
    assert m is not None, "cup & handle harus terdeteksi"
    assert m.name == "CUP_AND_HANDLE" and m.direction == "BULLISH"
    # kurva WAJIB melewati pivot ASLI (dasar 94.5 & rim 102/101.8)
    curve_prices = [pr for _, pr in m.curve]
    assert min(curve_prices) == pytest.approx(94.5, abs=0.6)
    assert len(m.curve) >= 8


def test_broken_cup_rejected_honestly():
    # koreksi handle terlalu dalam (>45% cup) = pola pecah -> tolak
    pivots = [
        (2, "HIGH", 108.0), (10, "LOW", 102.0),
        (18, "HIGH", 107.5), (30, "LOW", 94.5),
        (42, "HIGH", 107.0), (54, "LOW", 101.8),
        (64, "HIGH", 104.0), (74, "LOW", 97.0),   # terlalu dalam
        (82, "HIGH", 105.0),
    ]
    candles = _candles_from_pivots(pivots, tail_close=104.0)
    assert P._cup_handle_pattern(candles, _atr_of(candles)) is None


@pytest.mark.asyncio
async def test_chart_draws_curve_pattern(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.core.chart.generator import render_chart

    candles = _candles_from_pivots(CUP_HANDLE, tail_close=104.8)
    m = P._cup_handle_pattern(candles, _atr_of(candles))
    assert m is not None
    path = render_chart(pair="DEMOCUP", timeframe="M15", candles=candles,
                        patterns=[m])
    assert path.exists() and path.stat().st_size > 20_000
