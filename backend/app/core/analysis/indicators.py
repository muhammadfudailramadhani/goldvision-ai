"""Indikator teknikal (FASE 2+) — dihitung dari candle ASLI, kategori pilihan user.

Semua fungsi mengembalikan list sepanjang len(candles); nilai awal yang belum
terbentuk = None (jujur, bukan nol karangan). Ringkasan teks = fakta angka,
bukan saran.
"""
from dataclasses import dataclass

# kategori yang boleh dipilih user -> (label tampilan, tipe render)
INDICATOR_CATALOG: dict[str, tuple[str, str]] = {
    "sma": ("SMA 20/50", "overlay"),
    "ema": ("EMA 9/21", "overlay"),
    "bb": ("Bollinger Bands 20/2", "overlay"),
    "rsi": ("RSI 14", "panel"),
    "macd": ("MACD 12/26/9", "panel"),
    "stoch": ("Stochastic 14/3", "panel"),
    "obv": ("OBV", "panel"),
    "atr": ("ATR 14", "panel"),
}
ALIASES = {"bollinger": "bb", "bollinger_bands": "bb", "stochastic": "stoch",
           "semua": "__all__", "all": "__all__", "full": "__all__",
           "semua indikator": "__all__", "all indicators": "__all__",
           "indikator lengkap": "__all__"}


def normalize_selection(tokens) -> list[str]:
    """'rsi macd semua' -> daftar key katalog terurut kanonik."""
    wanted: set[str] = set()
    for t in tokens:
        t = ALIASES.get(str(t).lower(), str(t).lower())
        if t == "__all__":
            wanted |= set(INDICATOR_CATALOG)
        elif t in INDICATOR_CATALOG:
            wanted.add(t)
    order = list(INDICATOR_CATALOG)
    return [k for k in order if k in wanted]


@dataclass(frozen=True)
class IndicatorSeries:
    key: str
    label: str
    kind: str          # overlay | panel
    series: dict       # nama garis -> list[float | None]
    summary: str       # ringkasan nilai terakhir (fakta)


def _sma(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    for i in range(period - 1, len(values)):
        out[i] = sum(values[i - period + 1:i + 1]) / period
    return out


def _ema(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    k = 2 / (period + 1)
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    """Wilder RSI. Tren naik murni -> 100; turun murni -> 0."""
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    if avg_loss == 0:
        out[period] = 50.0 if avg_gain == 0 else 100.0
    else:
        out[period] = 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(d, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0.0)) / period
        if avg_loss == 0:
            out[i] = 50.0 if avg_gain == 0 else 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100 - 100 / (1 + rs)
    return out


def macd(closes: list[float], fast: int = 12, slow: int = 26,
         signal_p: int = 9) -> tuple[list, list, list]:
    ema_f, ema_s = _ema(closes, fast), _ema(closes, slow)
    line: list[float | None] = [None] * len(closes)
    start = next((i for i in range(len(closes))
                  if ema_f[i] is not None and ema_s[i] is not None), None)
    if start is not None:
        for i in range(start, len(closes)):
            line[i] = ema_f[i] - ema_s[i]
    compact = [v for v in line[start:] if v is not None] if start is not None else []
    sig_c = _ema(compact, signal_p) if compact else []
    signal: list[float | None] = [None] * len(closes)
    hist: list[float | None] = [None] * len(closes)
    if start is not None:
        for j, v in enumerate(sig_c):
            if v is not None:
                signal[start + j] = v
                base = line[start + j]
                hist[start + j] = base - v
    return line, signal, hist


def bollinger(closes: list[float], period: int = 20,
              mult: float = 2.0) -> tuple[list, list, list]:
    mid = _sma(closes, period)
    upper: list[float | None] = [None] * len(closes)
    lower: list[float | None] = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        sd = (sum((x - mid[i]) ** 2 for x in window) / period) ** 0.5
        upper[i] = mid[i] + mult * sd
        lower[i] = mid[i] - mult * sd
    return mid, upper, lower


def stochastic(candles: list, period: int = 14, smooth: int = 3) -> tuple[list, list]:
    n = len(candles)
    raw: list[float | None] = [None] * n
    for i in range(period - 1, n):
        hi = max(c.high for c in candles[i - period + 1:i + 1])
        lo = min(c.low for c in candles[i - period + 1:i + 1])
        raw[i] = 50.0 if hi == lo else (candles[i].close - lo) / (hi - lo) * 100
    compact = [(i, v) for i, v in enumerate(raw) if v is not None]
    k_vals = [_sma([v for _, v in compact], smooth)]
    k_line: list[float | None] = [None] * n
    d_line: list[float | None] = [None] * n
    ks = [v for _, v in compact]
    k_smoothed = _sma(ks, smooth)
    for j, (i, _) in enumerate(compact):
        k_line[i] = k_smoothed[j]
    d_compact = [(i, v) for i, v in zip([i for i, _ in compact], k_smoothed) if v is not None]
    ds = [v for _, v in d_compact]
    d_smoothed = _sma(ds, smooth)
    for j, (i, _) in enumerate(d_compact):
        d_line[i] = d_smoothed[j]
    return k_line, d_line


def obv(candles: list) -> list[float]:
    out = [0.0]
    for i in range(1, len(candles)):
        prev = out[-1]
        if candles[i].close > candles[i - 1].close:
            out.append(prev + candles[i].volume)
        elif candles[i].close < candles[i - 1].close:
            out.append(prev - candles[i].volume)
        else:
            out.append(prev)
    return out


def atr_series(candles: list, period: int = 14) -> list[float | None]:
    from .supply_demand import _atr

    out: list[float | None] = [None] * len(candles)
    for i in range(period, len(candles) + 1):
        out[i - 1] = _atr(candles[:i], period)
    return out


def compute(candles: list, keys: list[str]) -> list[IndicatorSeries]:
    """Hitung indikator terpilih. Return urut sesuai INDICATOR_CATALOG."""
    if not candles:
        return []
    closes = [c.close for c in candles]
    results: list[IndicatorSeries] = []

    def last(v):
        return next((x for x in reversed(v) if x is not None), None)

    for key in keys:
        if key == "sma":
            s20, s50 = _sma(closes, 20), _sma(closes, 50)
            l20, l50 = last(s20), last(s50)
            rel = ("di atas" if l20 and l50 and l20 > l50 else
                   "di bawah" if l20 and l50 else "menunggu")
            results.append(IndicatorSeries("sma", "SMA 20/50", "overlay",
                                           {"SMA20": s20, "SMA50": s50},
                                           f"SMA20 {l20:.5g} {rel} SMA50 {l50:.5g}"))
        elif key == "ema":
            e9, e21 = _ema(closes, 9), _ema(closes, 21)
            l9, l21 = last(e9), last(e21)
            rel = ("di atas" if l9 and l21 and l9 > l21 else
                   "di bawah" if l9 and l21 else "menunggu")
            results.append(IndicatorSeries("ema", "EMA 9/21", "overlay",
                                           {"EMA9": e9, "EMA21": e21},
                                           f"EMA9 {l9:.5g} {rel} EMA21 {l21:.5g}"))
        elif key == "bb":
            mid, up, lo = bollinger(closes)
            lu, price = last(up), closes[-1]
            pos = ""
            if lu is not None:
                width = (last(up) - last(lo)) if last(lo) else 0
                pos = " — harga di pita atas!" if price >= lu else ""
                results.append(IndicatorSeries(
                    "bb", "BB 20/2", "overlay",
                    {"BB Upper": up, "BB Mid": mid, "BB Lower": lo},
                    f"lebar pita {width:.5g}{pos}"))
        elif key == "rsi":
            r = rsi(closes)
            lr = last(r)
            zone = ("<70 netral" if lr is None else
                    "JENUH BELI (>70)" if lr >= 70 else
                    "JENUH JUAL (<30)" if lr <= 30 else "netral")
            results.append(IndicatorSeries("rsi", "RSI 14", "panel",
                                           {"RSI": r}, f"{lr:.1f} — {zone}" if lr is not None else "-"))
        elif key == "macd":
            line, sig, hist = macd(closes)
            lh, ls = last(hist), last(line)
            arrow = "↑ positif" if (lh or 0) > 0 else "↓ negatif"
            results.append(IndicatorSeries(
                "macd", "MACD 12/26/9", "panel",
                {"MACD": line, "Signal": sig},
                f"line {ls:.5g}, histogram {lh:+.5g} ({arrow})"
                if lh is not None else "-"))
        elif key == "stoch":
            k, d = stochastic(candles)
            lk, ld = last(k), last(d)
            zone = ("jenuh beli" if (lk or 50) >= 80 else
                    "jenuh jual" if (lk or 50) <= 20 else "netral")
            results.append(IndicatorSeries(
                "stoch", "Stoch 14/3", "panel", {"%K": k, "%D": d},
                f"%K {lk:.1f} / %D {ld:.1f} — {zone}" if lk is not None else "-"))
        elif key == "atr":
            a = atr_series(candles)
            la = last(a)
            results.append(IndicatorSeries("atr", "ATR 14", "panel",
                                           {"ATR": a},
                                           f"{la:.5g} (volatilitas)" if la else "-"))
        elif key == "obv":
            o = obv(candles)
            slope = o[-1] - o[max(len(o) - 11, 0)]
            results.append(IndicatorSeries(
                "obv", "OBV", "panel", {"OBV": o},
                f"{'naik' if slope > 0 else 'turun' if slope < 0 else 'datar'} "
                f"dalam 10 bar ({slope:+.0f})")
            )
    return results


def summarize(series_list: list[IndicatorSeries]) -> str:
    """Blok teks ringkasan untuk balasan bot — fakta angka, bukan saran."""
    if not series_list:
        return ""
    lines = ["", "\U0001f4ca Indikator:"]
    for s in series_list:
        lines.append(f"  • {s.label}: {s.summary}")
    lines.append("  \u26a0\ufe0f Fakta teknikal, bukan saran finansial.")
    return "\n".join(lines)
