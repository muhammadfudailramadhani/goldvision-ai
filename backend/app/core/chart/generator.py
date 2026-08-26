"""Chart generator (§11) — digambar sendiri dari market data, TIDAK scrape/screenshot TradingView.

Style: dark trading terminal, candlestick + wick, grid, right price scale, bottom time scale,
current price, pair+timeframe+timestamp. Overlay: S/R, supply/demand, entry/SL/TP1/TP2,
chart pattern (segitiga/wedge/channel/double top/H&S) — garis pola DITITIKKAN pada
pivot asli hasil deteksi, jadi bentuknya selalu sesuai data.
"""
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Polygon, Rectangle  # noqa: E402

OUTPUT_DIR = Path("generated/charts")

_BG = "#131722"
_GRID = "#2a2e39"
_UP = "#26a69a"
_DOWN = "#ef5350"
_TEXT = "#d1d4dc"
_ACCENT = "#2962ff"

_PATTERN_COLORS = ["#ffb300", "#00e5ff"]


def _draw_patterns(ax, patterns) -> list[Line2D]:
    """Gambar tiap pola: garis pivot asli, titik pivot, area pola, label.

    Garis TIDAK dikarang — koordinat x/y berasal dari PatternMatch.lines
    yang dibangun dari pivot riil di patterns.py.
    """
    legend_handles: list[Line2D] = []
    for k, pat in enumerate(patterns or []):
        color = _PATTERN_COLORS[k % len(_PATTERN_COLORS)]
        for li, line in enumerate(pat.lines):
            ax.plot([line.x0, line.x1], [line.y0, line.y1],
                    linestyle="--" if li else "-",
                    linewidth=1.5, color=color, alpha=0.9, zorder=4)
            # ekstensi menuju apex (konvergensi) bila ada & masih di depan
            if pat.apex_x and pat.apex_x > line.x1:
                ax.plot([line.x1, pat.apex_x], [line.y1, line.slope * pat.apex_x
                                                + (line.y1 - line.slope * line.x1)],
                        linestyle=":", linewidth=1.0, color=color, alpha=0.55, zorder=4)

        # kurva pola (mis. parabola Cup & Handle) — titik dari pivot ASLI
        if pat.curve:
            cx = [p[0] for p in pat.curve]
            cy = [p[1] for p in pat.curve]
            ax.plot(cx, cy, linestyle="-", linewidth=1.8, color=color,
                    alpha=0.95, zorder=4)

        # area pola antara dua garis pertama (bila sejajar struktur band)
        if len(pat.lines) >= 2:
            l1, l2 = pat.lines[0], pat.lines[1]
            verts = [(l1.x0, l1.y0), (l1.x1, l1.y1),
                     (l2.x1, l2.y1), (l2.x0, l2.y0)]
            ax.add_patch(Polygon(verts, closed=True, facecolor=color,
                                 alpha=0.07, edgecolor="none", zorder=1))

        for idx, price, kind in pat.points:
            ax.scatter(idx, price, s=26, marker="v" if kind == "HIGH" else "^",
                       color=color, edgecolors=_BG, linewidths=0.5, zorder=5)

        y_label = min(p[1] for p in pat.points)
        ax.text(pat.points[0][0] if pat.points else 4, y_label,
                f"{pat.name_id} · {int(pat.confidence * 100)}%",
                fontsize=8, color=color, fontweight="bold",
                va="top", ha="left", zorder=6,
                bbox=dict(boxstyle="round,pad=0.25", facecolor=_BG,
                          edgecolor=color, alpha=0.85))

        legend_handles.append(Line2D([0], [0], color=color, lw=1.6, linestyle="--",
                                     label=f"{pat.name_id} ({int(pat.confidence * 100)}%)"))
    return legend_handles


def render_chart(
    pair: str,
    timeframe: str,
    candles: list,
    levels: list | None = None,
    zones: list | None = None,
    entry: float | None = None,
    sl: float | None = None,
    tp1: float | None = None,
    tp2: float | None = None,
    patterns: list | None = None,
    indicators: list | None = None,
    out_dir: Path | None = None,
) -> Path:
    if not candles:
        raise ValueError("tidak ada candle untuk digambar")
    out_dir = out_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    # defense-in-depth: pair hanya boleh [a-z0-9_] untuk nama file
    safe_pair = "".join(ch for ch in pair.lower() if ch.isalnum() or ch == "_") or "pair"

    indicators = indicators or []
    panel_items = [s for s in indicators if s.kind == "panel"]
    n_panels = len(panel_items)
    fig, axes = plt.subplots(
        n_panels + 1, figsize=(12, 6 + 1.7 * n_panels), dpi=110, sharex=True,
        gridspec_kw={"height_ratios": [3] + [1] * n_panels})
    axes = axes if n_panels else [axes]
    ax = axes[0]
    fig.patch.set_facecolor(_BG)
    for a in axes:
        a.set_facecolor(_BG)

    xs = range(len(candles))
    for i, c in enumerate(candles):
        color = _UP if c.close >= c.open else _DOWN
        ax.plot([i, i], [c.low, c.high], color=color, linewidth=0.9, zorder=2)
        body_low, body_high = min(c.open, c.close), max(c.open, c.close)
        ax.add_patch(Rectangle((i - 0.35, body_low), 0.7, max(body_high - body_low, 1e-9),
                               facecolor=color, edgecolor=color, zorder=3))

    for lvl in levels or []:
        color = "#42a5f5" if lvl.kind == "SUPPORT" else "#ef9a9a"
        ax.axhline(lvl.price, color=color, linestyle="--", linewidth=0.8, alpha=0.7)
        ax.text(len(candles) + 1, lvl.price, f"{lvl.kind[0]} {lvl.price:g}", fontsize=7, color=color, va="center")

    for z in zones or []:
        color = "#1b5e20" if z.kind == "DEMAND" else "#7f1d1d"
        ax.axhspan(z.low, z.high, color=color, alpha=0.25, zorder=1)
        ax.text(2, (z.low + z.high) / 2, z.kind, fontsize=7, color=_TEXT, va="center", alpha=0.8)

    for value, label, color in ((entry, "ENTRY", _ACCENT), (sl, "SL", _DOWN), (tp1, "TP1", _UP), (tp2, "TP2", "#66bb6a")):
        if value is not None:
            ax.axhline(value, color=color, linewidth=1.1)
            ax.text(len(candles) + 1, value, f"{label} {value:g}", fontsize=7, color=color, va="center", fontweight="bold")

    price = candles[-1].close
    ax.axhline(price, color="#fdd835", linewidth=0.9, linestyle=":")
    ax.text(0.3, price, f" {price:g}", fontsize=8, color="#fdd835", va="bottom", fontweight="bold")

    # ---- overlay indikator di chart utama (SMA/EMA/Bollinger) ----
    _OVERLAY_COLORS = {"SMA20": "#ff7043", "SMA50": "#ffa726", "EMA9": "#40c4ff",
                       "EMA21": "#448aff", "BB Upper": "#9575cd",
                       "BB Mid": "#b39ddb", "BB Lower": "#9575cd"}
    n = len(candles)

    def _plot_line(a, values, color, label, lw=1.1):
        pts = [(i, v) for i, v in enumerate(values) if v is not None]
        if pts:
            a.plot([p[0] for p in pts], [p[1] for p in pts], color=color,
                   linewidth=lw, label=label, zorder=4)

    for s in indicators:
        if s.kind != "overlay":
            continue
        plotted_any = False
        for line_name, values in s.series.items():
            before = len(ax.lines)
            _plot_line(ax, values, _OVERLAY_COLORS.get(line_name, "#b0bec5"), line_name)
            plotted_any = plotted_any or len(ax.lines) > before
        if plotted_any:
            ax.legend(loc="lower right", fontsize=6.5, framealpha=0.25,
                      facecolor=_BG, edgecolor=_GRID, labelcolor=_TEXT)

    step = max(len(candles) // 6, 1)
    ticks = list(range(0, len(candles), step))
    tick_labels = [datetime.fromtimestamp(candles[t].ts, tz=timezone.utc).strftime("%m-%d %H:%M")
                   for t in ticks]

    # ---- panel osilator (RSI/MACD/Stoch/OBV/ATR) ----
    for pi, s in enumerate(panel_items):
        p = axes[pi + 1]
        p.grid(color=_GRID, linestyle="-", linewidth=0.4, alpha=0.5)
        p.set_ylabel(s.label, color=_TEXT, fontsize=7)
        p.tick_params(colors=_TEXT, labelsize=6.5)
        for spine in p.spines.values():
            spine.set_color(_GRID)
        if s.key == "rsi":
            _plot_line(p, s.series["RSI"], "#ab47bc", "RSI", 1.2)
            p.axhline(70, color=_DOWN, linewidth=0.7, linestyle="--", alpha=0.7)
            p.axhline(30, color=_UP, linewidth=0.7, linestyle="--", alpha=0.7)
            p.set_ylim(0, 100)
        elif s.key == "macd":
            hist = s.series.get("MACD")
            sig = s.series.get("Signal")
            if hist:
                bars = [(i, v) for i, v in enumerate(hist) if v is not None]
                if bars:
                    p.bar([b[0] for b in bars],
                          [b[1] for b in bars],
                          color=[_UP if b[1] >= 0 else _DOWN for b in bars],
                          width=0.8, alpha=0.6)
            _plot_line(p, hist or [], "#42a5f5", "MACD", 1.1)
            _plot_line(p, sig or [], "#ff8a65", "Signal", 1.0)
            p.axhline(0, color=_GRID, linewidth=0.6)
        elif s.key == "stoch":
            _plot_line(p, s.series["%K"], "#42a5f5", "%K", 1.1)
            _plot_line(p, s.series["%D"], "#ff8a65", "%D", 1.0)
            p.axhline(80, color=_DOWN, linewidth=0.7, linestyle="--", alpha=0.7)
            p.axhline(20, color=_UP, linewidth=0.7, linestyle="--", alpha=0.7)
            p.set_ylim(0, 100)
        elif s.key == "obv":
            _plot_line(p, s.series["OBV"], "#26c6da", "OBV", 1.1)
        elif s.key == "atr":
            _plot_line(p, s.series["ATR"], "#ffee58", "ATR", 1.1)
        p.set_xlim(-1, n + 8)

    # label waktu hanya di panel paling bawah
    axes[-1].set_xticks(ticks)
    axes[-1].set_xticklabels(tick_labels, fontsize=7, color=_TEXT)

    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.tick_params(colors=_TEXT, labelsize=7)
    for a in axes:
        for spine in a.spines.values():
            spine.set_color(_GRID)
    ax.grid(color=_GRID, linestyle="-", linewidth=0.4, alpha=0.6)
    ax.set_xlim(-1, len(candles) + 8)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ax.set_title(f"{pair} · {timeframe} · {stamp}", color=_TEXT, fontsize=11, loc="left")

    legend = _draw_patterns(ax, patterns)
    if legend:
        ax.legend(handles=legend, loc="upper left", fontsize=7, framealpha=0.3,
                  facecolor=_BG, edgecolor=_GRID, labelcolor=_TEXT)

    fig.tight_layout()

    path = out_dir / f"{safe_pair}_{timeframe.lower()}.png"
    fig.savefig(path, facecolor=_BG)
    plt.close(fig)
    return path
