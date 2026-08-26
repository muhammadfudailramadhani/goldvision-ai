"""Chart pattern detection (FASE 2+) — rule-based dari PIVOT ASLI, bukan tebakan.

Prinsip wajib:
1. Semua garis tren yang dilaporkan DITITIK-KAN pada koordinat pivot nyata
   (index bar + harga pivot hasil find_pivots) -> gambar selalu sesuai data.
2. Tidak ada pola lolos aturan = tidak ada pola dilaporkan (jangan mengarang).
3. Confidence dari jumlah sentuhan garis & kualitas struktur, bukan angka acak.

Pola yang didukung:
- Segitiga : ASCENDING_TRIANGLE, DESCENDING_TRIANGLE, SYMMETRICAL_TRIANGLE
- Wedge    : RISING_WEDGE, FALLING_WEDGE
- Channel  : CHANNEL_UP, CHANNEL_DOWN, RECTANGLE
- Reversal : DOUBLE_TOP/BOTTOM, TRIPLE_TOP/BOTTOM, HEAD_SHOULDERS (+inverse),
             CUP_AND_HANDLE
- Kontinuasi: BULL_FLAG, BEAR_FLAG, PENNANT
"""
from dataclasses import dataclass, field

import numpy as np

from .market_structure import Pivot, find_pivots
from .supply_demand import _atr

LOOKBACK_BARS = 90      # jendela pencarian pola (bar M15 terakhir)
FLAT_RISE = 0.5         # "datar": gerak total garis < 0.5 ATR sepanjang pola
MIN_RISE = 0.8          # "menanjak/turun": gerak total >= 0.8 ATR
PARALLEL_TOL = 0.7      # channel: selisih dua garis stabil < 0.7 ATR
MIN_SPAN = 12           # pola terlalu pendek = bukan pola
MAX_PATTERNS = 3        # maksimal pola ditampilkan agar chart tak ramai
POLE_MIN_ATR = 2.5      # ketinggian minimum tiang flag/pennant
POLE_MAX_BARS = 18      # panjang maksimum tiang


@dataclass(frozen=True)
class PatternLine:
    """Garis yang DITITIKKAN pada pivot asli — untuk deteksi & penggambaran."""
    x0: int
    y0: float
    x1: int
    y1: float

    @property
    def slope(self) -> float:
        return (self.y1 - self.y0) / max(self.x1 - self.x0, 1)


@dataclass(frozen=True)
class PatternMatch:
    name: str           # id pola (ASCENDING_TRIANGLE ...)
    name_id: str        # nama Indonesia untuk tampilan
    direction: str      # BULLISH | BEARISH | NEUTRAL
    confidence: float   # 0..1
    points: list = field(default_factory=list)   # [(idx, price, kind)]
    lines: list = field(default_factory=list)    # [PatternLine] pivot asli
    curve: list = field(default_factory=list)    # [(idx, price)] kurva (cup)
    apex_x: int | None = None                    # konvergensi segitiga/wedge
    note: str = ""


def _fit_line(pivots: list[Pivot]) -> tuple[float, float] | None:
    """Least squares melalui pivot ASLI. Return (slope, intercept) atau None."""
    xs = np.array([p.index for p in pivots], dtype=float)
    ys = np.array([p.price for p in pivots], dtype=float)
    if len(xs) < 2:
        return None
    if len(xs) == 2:
        m = (ys[1] - ys[0]) / max(xs[1] - xs[0], 1)
        return m, ys[0] - m * xs[0]
    m, b = np.polyfit(xs, ys, 1)
    return float(m), float(b)


def _line_pattern(candles: list, atr: float) -> PatternMatch | None:
    """Segitiga / wedge / channel dari fit garis resistance & support ASLI."""
    n = len(candles)
    pivots = [p for p in find_pivots(candles, window=2)
              if p.index >= n - LOOKBACK_BARS]
    highs = [p for p in pivots if p.kind == "HIGH"][-3:]
    lows = [p for p in pivots if p.kind == "LOW"][-3:]
    if len(highs) < 2 or len(lows) < 2:
        return None

    fh, fl = _fit_line(highs), _fit_line(lows)
    if not fh or not fl:
        return None
    (mh, bh), (ml, bl) = fh, fl

    x_start = min(highs[0].index, lows[0].index)
    span = max(n - 1 - x_start, MIN_SPAN)

    # garis utk digambar: dari pivot pertama -> bar terakhir (ekstensi apa adanya)
    line_hi = PatternLine(x_start, mh * x_start + bh, n - 1, mh * (n - 1) + bh)
    line_lo = PatternLine(x_start, ml * x_start + bl, n - 1, ml * (n - 1) + bl)

    # harga sekarang harus DI DALAM kedua garis (pola masih terbentuk)
    price = candles[-1].close
    yh, yl = line_hi.y1, line_lo.y1
    if not (yh >= price - 0.05 * atr and price >= yl - 0.05 * atr):
        return None

    rh, rl = (mh * span) / atr, (ml * span) / atr  # gerak total dalam satuan ATR
    conv = (ml - mh) * span                        # konvergensi > 0 jika menyempit

    def conf(kind_high="HIGH", kind_low="LOW", m_h=mh, b_h=bh, m_l=ml, b_l=bl):
        th = _touch_count(pivots, kind_high, m_h, b_h, tol=atr * 0.25)
        tl = _touch_count(pivots, kind_low, m_l, b_l, tol=atr * 0.25)
        return min(0.45 + 0.11 * (th + tl), 0.95)

    # --- segitiga: satu sisi DATAR ---
    if abs(rh) <= FLAT_RISE and rl >= MIN_RISE:
        apex = _apex_x(mh, bh, ml, bl)
        return PatternMatch("ASCENDING_TRIANGLE", "Ascending Triangle", "BULLISH",
                            conf(), points=_pts(highs + lows),
                            lines=[line_hi, line_lo], apex_x=apex,
                            note="resistensi datar + support menanjak")
    if abs(rl) <= FLAT_RISE and rh <= -MIN_RISE:
        apex = _apex_x(mh, bh, ml, bl)
        return PatternMatch("DESCENDING_TRIANGLE", "Descending Triangle", "BEARISH",
                            conf(), points=_pts(highs + lows),
                            lines=[line_hi, line_lo], apex_x=apex,
                            note="support datar + resistensi menurun")
    if rh <= -MIN_RISE and rl >= MIN_RISE:
        apex = _apex_x(mh, bh, ml, bl)
        return PatternMatch("SYMMETRICAL_TRIANGLE", "Segitiga Simetris", "NEUTRAL",
                            conf(), points=_pts(highs + lows),
                            lines=[line_hi, line_lo], apex_x=apex,
                            note="kedua sisi saling mendekat")

    # --- wedge: sama arah tapi menyempit ---
    if rh >= MIN_RISE and rl >= MIN_RISE and conv > PARALLEL_TOL:
        return PatternMatch("RISING_WEDGE", "Rising Wedge", "BEARISH",
                            conf(), points=_pts(highs + lows),
                            lines=[line_hi, line_lo],
                            apex_x=_apex_x(mh, bh, ml, bl),
                            note="naik tapi melebar-lalu-menyempit (kelelahan beli)")
    if rh <= -MIN_RISE and rl <= -MIN_RISE and conv > PARALLEL_TOL:
        return PatternMatch("FALLING_WEDGE", "Falling Wedge", "BULLISH",
                            conf(), points=_pts(highs + lows),
                            lines=[line_hi, line_lo],
                            apex_x=_apex_x(mh, bh, ml, bl),
                            note="turun namun menjual melemah (kontraksi)")

    # --- channel: paralel / rectangle ---
    spread_now = yh - yl
    spread_start = line_hi.y0 - line_lo.y0
    if abs(rh) <= FLAT_RISE and abs(rl) <= FLAT_RISE:
        if spread_now >= 1.5 * atr:
            return PatternMatch("RECTANGLE", "Rectangle / Range", "NEUTRAL",
                                conf(), points=_pts(highs + lows),
                                lines=[line_hi, line_lo],
                                note="konsolidasi datar, tunggu breakout")
    if spread_start > 0 and abs(spread_now - spread_start) <= PARALLEL_TOL * atr:
        if rh >= MIN_RISE and rl >= MIN_RISE:
            return PatternMatch("CHANNEL_UP", "Channel Up", "BULLISH",
                                conf(), points=_pts(highs + lows),
                                lines=[line_hi, line_lo], note="tren naik teratur")
        if rh <= -MIN_RISE and rl <= -MIN_RISE:
            return PatternMatch("CHANNEL_DOWN", "Channel Down", "BEARISH",
                                conf(), points=_pts(highs + lows),
                                lines=[line_hi, line_lo], note="tren turun teratur")
    return None


def _touch_count(pivots: list[Pivot], kind: str, m: float, b: float, tol: float) -> int:
    return sum(1 for p in pivots if p.kind == kind and abs(p.price - (m * p.index + b)) <= tol)


def _apex_x(mh: float, bh: float, ml: float, ml_b: float) -> int | None:
    """Perpotongan dua garis (konvergensi)."""
    if abs(mh - ml) < 1e-12:
        return None
    x = (ml_b - bh) / (mh - ml)
    return int(round(x)) if x > 0 else None


def _pts(*groups: list[Pivot]) -> list:
    return [(p.index, p.price, p.kind) for g in groups for p in g]


def _double_pattern(candles: list, atr: float) -> PatternMatch | None:
    """Double Top / Double Bottom: dua ekstrem selevel + lembah/puncak tengah cukup dalam."""
    n = len(candles)
    pivots = [p for p in find_pivots(candles, window=2)
              if p.index >= n - LOOKBACK_BARS]
    highs = [p for p in pivots if p.kind == "HIGH"]
    lows = [p for p in pivots if p.kind == "LOW"]

    # DOUBLE TOP: pasangan high terakhir
    if len(highs) >= 2 and len(lows) >= 1:
        h2, h1 = highs[-1], highs[-2]
        gap = h2.index - h1.index
        between = [p for p in lows if h1.index < p.index < h2.index]
        if gap >= 8 and between and abs(h1.price - h2.price) <= 0.45 * atr:
            neck = min(between, key=lambda p: p.price)
            depth = min(h1.price, h2.price) - neck.price
            if depth >= 1.2 * atr:
                line = PatternLine(h1.index, h1.price, h2.index, h2.price)  # puncak-puncak
                neck_line = PatternLine(neck.index, neck.price, h2.index, neck.price)
                return PatternMatch(
                    "DOUBLE_TOP", "Double Top", "BEARISH", 0.72,
                    points=[(h1.index, h1.price, "HIGH"), (neck.index, neck.price, "LOW"),
                            (h2.index, h2.price, "HIGH")],
                    lines=[line, neck_line],
                    note=f"dua puncak selevel, neckline {neck.price:g}")

    # DOUBLE BOTTOM: cermin
    if len(lows) >= 2 and len(highs) >= 1:
        l2, l1 = lows[-1], lows[-2]
        gap = l2.index - l1.index
        between = [p for p in highs if l1.index < p.index < l2.index]
        if gap >= 8 and between and abs(l1.price - l2.price) <= 0.45 * atr:
            neck = max(between, key=lambda p: p.price)
            height = neck.price - max(l1.price, l2.price)
            if height >= 1.2 * atr:
                line = PatternLine(l1.index, l1.price, l2.index, l2.price)
                neck_line = PatternLine(neck.index, neck.price, l2.index, neck.price)
                return PatternMatch(
                    "DOUBLE_BOTTOM", "Double Bottom", "BULLISH", 0.72,
                    points=[(l1.index, l1.price, "LOW"), (neck.index, neck.price, "HIGH"),
                            (l2.index, l2.price, "LOW")],
                    lines=[line, neck_line],
                    note=f"dua dasar selevel, neckline {neck.price:g}")
    return None


def _hs_pattern(candles: list, atr: float) -> PatternMatch | None:
    """Head & Shoulders (+inverse): 3 puncak, kepala tertinggi, bahu selevel."""
    n = len(candles)
    pivots = [p for p in find_pivots(candles, window=2)
              if p.index >= n - LOOKBACK_BARS]
    highs = [p for p in pivots if p.kind == "HIGH"]
    lows = [p for p in pivots if p.kind == "LOW"]

    if len(highs) >= 3 and len(lows) >= 2:
        ls, head, rs = highs[-3], highs[-2], highs[-1]
        t1 = [p for p in lows if ls.index < p.index < head.index]
        t2 = [p for p in lows if head.index < p.index < rs.index]
        if t1 and t2:
            shoulder_diff = abs(ls.price - rs.price)
            head_margin = head.price - max(ls.price, rs.price)
            if head_margin >= 1.0 * atr and shoulder_diff <= 0.7 * atr \
                    and rs.index - ls.index >= 14:
                nl_a, nl_b = t1[-1], t2[-1]
                return PatternMatch(
                    "HEAD_SHOULDERS", "Head & Shoulders", "BEARISH", 0.78,
                    points=[(ls.index, ls.price, "HIGH"), (head.index, head.price, "HIGH"),
                            (rs.index, rs.price, "HIGH"),
                            (nl_a.index, nl_a.price, "LOW"), (nl_b.index, nl_b.price, "LOW")],
                    lines=[PatternLine(ls.index, ls.price, head.index, head.price),
                           PatternLine(head.index, head.price, rs.index, rs.price),
                           PatternLine(nl_a.index, nl_a.price, nl_b.index, nl_b.price)],
                    note=f"kepala {head.price:g} menonjol, neckline via {nl_a.price:g}-{nl_b.price:g}")

    # INVERSE: tiga dasar, kepala terendah
    if len(lows) >= 3 and len(highs) >= 2:
        ls, head, rs = lows[-3], lows[-2], lows[-1]
        t1 = [p for p in highs if ls.index < p.index < head.index]
        t2 = [p for p in highs if head.index < p.index < rs.index]
        if t1 and t2:
            shoulder_diff = abs(ls.price - rs.price)
            head_margin = min(ls.price, rs.price) - head.price
            if head_margin >= 1.0 * atr and shoulder_diff <= 0.7 * atr \
                    and rs.index - ls.index >= 14:
                nl_a, nl_b = t1[-1], t2[-1]
                return PatternMatch(
                    "INV_HEAD_SHOULDERS", "Inverse Head & Shoulders", "BULLISH", 0.78,
                    points=[(ls.index, ls.price, "LOW"), (head.index, head.price, "LOW"),
                            (rs.index, rs.price, "LOW"),
                            (nl_a.index, nl_a.price, "HIGH"), (nl_b.index, nl_b.price, "HIGH")],
                    lines=[PatternLine(ls.index, ls.price, head.index, head.price),
                           PatternLine(head.index, head.price, rs.index, rs.price),
                           PatternLine(nl_a.index, nl_a.price, nl_b.index, nl_b.price)],
                    note=f"kepala terbalik di {head.price:g}")
    return None


def _flag_pennant_pattern(candles: list, atr: float) -> PatternMatch | None:
    """Bull/Bear Flag & Pennant: tiang impulsif tajam lalu konsolidasi kecil.

    Tiang = dua pivot berurutan dengan gerak >= POLE_MIN_ATR dalam <= POLE_MAX_BARS.
    Bendera = kanal kecil melawan/menyamping; Pennant = segitiga kecil menyempit.
    """
    n = len(candles)
    pivots = [p for p in find_pivots(candles, window=2)
              if p.index >= n - LOOKBACK_BARS]
    if len(pivots) < 5:
        return None

    # kumpulkan kandidat tiang, coba dari yang BESAR dulu (tiang sejati)
    candidates = []
    for a, b in zip(pivots, pivots[1:]):
        if b.index < n - 45:  # tiang harus masih dalam jendela recent
            continue
        pole = abs(b.price - a.price)
        if pole < POLE_MIN_ATR * atr or not (0 < b.index - a.index <= POLE_MAX_BARS):
            continue
        candidates.append((pole, a, b))
    candidates.sort(key=lambda t: t[0], reverse=True)

    for pole, a, b in candidates:
        direction = "BULLISH" if b.price > a.price else "BEARISH"
        bull = b.price > a.price

        # jendela konsolidasi setelah ujung tiang
        win = [p for p in pivots if b.index < p.index <= n - 1]
        if len([p for p in win if p.kind == "HIGH"]) < 2 or \
                len([p for p in win if p.kind == "LOW"]) < 2:
            continue
        highs = [p for p in win if p.kind == "HIGH"][-3:]
        lows = [p for p in win if p.kind == "LOW"][-3:]
        fh, fl = _fit_line(highs), _fit_line(lows)
        if not fh or not fl:
            continue
        (mh, bh), (ml, bl) = fh, fl

        price = candles[-1].close
        yh, yl = mh * (n - 1) + bh, ml * (n - 1) + bl
        tol_edge = 0.35 * atr  # konsolidasi boleh sedikit keluar garis
        if not (yh + tol_edge >= price and price >= yl - tol_edge):
            continue

        flag_span = n - 1 - b.index
        if flag_span < 4:
            continue
        rh, rl = mh * max(flag_span, 1) / atr, ml * max(flag_span, 1) / atr
        conv = (ml - mh) * flag_span
        # bendera KECIL dibanding tiang: lebar <= 35% tinggi tiang (min 1 ATR)
        spread_ok = (yh - yl) <= max(1.0 * atr, 0.35 * pole)

        if not spread_ok:
            continue

        th = _touch_count(pivots, "HIGH", mh, bh, tol=atr * 0.3)
        tl = _touch_count(pivots, "LOW", ml, bl, tol=atr * 0.3)
        conf = min(0.55 + 0.09 * (th + tl), 0.92)

        pole_line = PatternLine(a.index, a.price, b.index, b.price)
        hi_line = PatternLine(highs[0].index, mh * highs[0].index + bh,
                              n - 1, yh)
        lo_line = PatternLine(lows[0].index, ml * lows[0].index + bl,
                              n - 1, yl)

        if conv > PARALLEL_TOL:
            return PatternMatch("PENNANT", f"Pennant ({'Bull' if bull else 'Bear'})",
                                direction, conf,
                                points=_pts([a, b] + highs + lows),
                                lines=[pole_line, hi_line, lo_line],
                                apex_x=_apex_x(mh, bh, ml, bl),
                                note=f"tiang {pole / atr:.1f} ATR + konsolidasi menyempit")
        # flag: drift melawan arah tiang atau nyaris datar
        drift_ok_bull = (mh <= FLAT_RISE / max(flag_span, 1) * atr) if bull else True
        drift_ok_bear = (mh >= -FLAT_RISE / max(flag_span, 1) * atr) if not bull else True
        if drift_ok_bull and drift_ok_bear:
            return PatternMatch("BULL_FLAG" if bull else "BEAR_FLAG",
                                f"Bull Flag" if bull else "Bear Flag",
                                direction, conf,
                                points=_pts([a, b] + highs + lows),
                                lines=[pole_line, hi_line, lo_line],
                                note=f"tiang {pole / atr:.1f} ATR + bendera miring turun"
                                if bull else f"tiang {pole / atr:.1f} ATR + bendera naik")
    return None


def _triple_pattern(candles: list, atr: float) -> PatternMatch | None:
    """Triple Top/Bottom: tiga ekstrem selevel + lembah antara cukup dalam."""
    n = len(candles)
    pivots = [p for p in find_pivots(candles, window=2)
              if p.index >= n - LOOKBACK_BARS]
    highs = [p for p in pivots if p.kind == "HIGH"]
    lows = [p for p in pivots if p.kind == "LOW"]

    if len(highs) >= 3 and len(lows) >= 2:
        h1, h2, h3 = highs[-3], highs[-2], highs[-1]
        tops = sorted([h1.price, h2.price, h3.price])
        flat = (tops[2] - tops[0]) <= 0.7 * atr
        troughs = [p for p in lows if h1.index < p.index < h3.index]
        if flat and len(troughs) >= 2 and h3.index - h1.index >= 20:
            depth = min(h1.price, h2.price, h3.price) - \
                min(troughs[0].price, troughs[-1].price)
            if depth >= 1.5 * atr:
                neck = round((troughs[0].price + troughs[-1].price) / 2, 5)
                return PatternMatch(
                    "TRIPLE_TOP", "Triple Top", "BEARISH", 0.75,
                    points=[(p.index, p.price, "HIGH") for p in (h1, h2, h3)] +
                           [(t.index, t.price, "LOW") for t in (troughs[0], troughs[-1])],
                    lines=[PatternLine(h1.index, h1.price, h3.index, h3.price),
                           PatternLine(troughs[0].index, neck, h3.index, neck)],
                    note=f"tiga puncak gagal tembus ~{tops[1]:g}, neckline {neck:g}")

    if len(lows) >= 3 and len(highs) >= 2:
        l1, l2, l3 = lows[-3], lows[-2], lows[-1]
        bases = sorted([l1.price, l2.price, l3.price])
        flat = (bases[2] - bases[0]) <= 0.7 * atr
        peaks = [p for p in highs if l1.index < p.index < l3.index]
        if flat and len(peaks) >= 2 and l3.index - l1.index >= 20:
            height = max(peaks[0].price, peaks[-1].price) - \
                min(l1.price, l2.price, l3.price)
            if height >= 1.5 * atr:
                neck = round((peaks[0].price + peaks[-1].price) / 2, 5)
                return PatternMatch(
                    "TRIPLE_BOTTOM", "Triple Bottom", "BULLISH", 0.75,
                    points=[(p.index, p.price, "LOW") for p in (l1, l2, l3)] +
                           [(p.index, p.price, "HIGH") for p in (peaks[0], peaks[-1])],
                    lines=[PatternLine(l1.index, l1.price, l3.index, l3.price),
                           PatternLine(peaks[0].index, neck, l3.index, neck)],
                    note=f"tiga dasar bertahan ~{bases[1]:g}, neckline {neck:g}")
    return None


def _cup_handle_pattern(candles: list, atr: float) -> PatternMatch | None:
    """Cup & Handle: dasar membulat (kurva parabola lewat pivot ASLI) + handle kecil."""
    n = len(candles)
    pivots = [p for p in find_pivots(candles, window=2)
              if p.index >= n - LOOKBACK_BARS]
    lows = [p for p in pivots if p.kind == "LOW"]
    highs = [p for p in pivots if p.kind == "HIGH"]
    if len(lows) < 3 or not highs:  # minimal rim-bawah-rim
        return None

    bottom = min(lows, key=lambda p: p.price)
    lefts = [p for p in lows if p.index < bottom.index]
    rights = [p for p in lows if p.index > bottom.index]
    if not lefts or not rights:
        return None
    rim_l = lefts[-1]   # rim kiri terdekat sebelum dasar
    rim_r = rights[0]   # rim kanan pertama sesudah dasar
    width = rim_r.index - rim_l.index
    depth = rim_l.price - bottom.price
    rim_diff = abs(rim_l.price - rim_r.price)
    if width < 25 or depth < 2.5 * atr or rim_diff > 0.8 * atr:
        return None

    cup_lows = [p for p in lows if rim_l.index <= p.index <= rim_r.index]
    xs = np.array([p.index for p in cup_lows], dtype=float)
    ys = np.array([p.price for p in cup_lows], dtype=float)
    coef = np.polyfit(xs, ys, 2)  # parabola melalui pivot ASLI
    curve_x = np.linspace(rim_l.index, rim_r.index, max(width, 8))
    curve = [(int(round(x)), float(np.polyval(coef, x))) for x in curve_x]

    # handle: setelah rim kanan, koreksi kecil TIDAK lebih dalam dari 45% kedalaman cup
    after = [p for p in pivots if p.index > rim_r.index]
    handle_high = next((p for p in reversed(after) if p.kind == "HIGH"), None)
    if after:
        pullback = rim_r.price - min(p.price for p in after)
        if pullback > 0.45 * depth:
            return None  # koreksi terlalu dalam = cup pecah, jujur tolak

    pts = [(rim_l.index, rim_l.price, "LOW"), (bottom.index, bottom.price, "LOW"),
           (rim_r.index, rim_r.price, "LOW")]
    if handle_high:
        pts.append((handle_high.index, handle_high.price, "HIGH"))
    target = rim_l.price + depth  # proyeksi klasik
    return PatternMatch(
        "CUP_AND_HANDLE", "Cup & Handle", "BULLISH", 0.74,
        points=pts, lines=[PatternLine(rim_r.index, rim_r.price, n - 1,
                                       min(target, candles[-1].high))],
        curve=curve,
        note=f"dasar bulat {bottom.price:g}, rim selevel, proyeksi {target:g}")


def detect_patterns(candles: list) -> list[PatternMatch]:
    """Deteksi pola pada candle riil. Return maksimal MAX_PATTERNS terbaik."""
    if len(candles) < MIN_SPAN + 10:
        return []
    atr = _atr(candles)
    if atr <= 0:
        return []

    found: list[PatternMatch] = []
    for detector in (_hs_pattern, _line_pattern, _double_pattern,
                     _triple_pattern, _cup_handle_pattern, _flag_pennant_pattern):
        try:
            match = detector(candles, atr)
        except Exception:
            match = None  # deteksi satu pola gagal = skip pola itu, bukan crash
        if match is not None:
            found.append(match)

    # urutkan confidence, ambil terbaik dengan nama unik
    seen: set[str] = set()
    result: list[PatternMatch] = []
    for m in sorted(found, key=lambda x: x.confidence, reverse=True):
        if m.name in seen:
            continue
        seen.add(m.name)
        result.append(m)
        if len(result) >= MAX_PATTERNS:
            break
    return result
