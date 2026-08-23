"""Chart generator (§11) — digambar sendiri dari market data, TIDAK scrape/screenshot TradingView.

Style: dark trading terminal, candlestick + wick, grid, right price scale, bottom time scale,
current price, pair+timeframe+timestamp. Overlay: S/R, supply/demand, entry/SL/TP1/TP2,
optional BOS/CHoCH/OB/FVG.
"""
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

OUTPUT_DIR = Path("generated/charts")

_BG = "#131722"
_GRID = "#2a2e39"
_UP = "#26a69a"
_DOWN = "#ef5350"
_TEXT = "#d1d4dc"
_ACCENT = "#2962ff"


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
    out_dir: Path | None = None,
) -> Path:
    if not candles:
        raise ValueError("tidak ada candle untuk digambar")
    out_dir = out_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6), dpi=110)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)

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

    step = max(len(candles) // 6, 1)
    ticks = list(range(0, len(candles), step))
    ax.set_xticks(ticks)
    ax.set_xticklabels(
        [datetime.fromtimestamp(candles[t].ts, tz=timezone.utc).strftime("%m-%d %H:%M") for t in ticks],
        fontsize=7, color=_TEXT,
    )
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.tick_params(colors=_TEXT, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color(_GRID)
    ax.grid(color=_GRID, linestyle="-", linewidth=0.4, alpha=0.6)
    ax.set_xlim(-1, len(candles) + 8)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ax.set_title(f"{pair} · {timeframe} · {stamp}", color=_TEXT, fontsize=11, loc="left")
    fig.tight_layout()

    path = out_dir / f"{pair.lower()}_{timeframe.lower()}.png"
    fig.savefig(path, facecolor=_BG)
    plt.close(fig)
    return path
