"""Backtest — walk-forward replay candle historis terhadap pipeline asli (docs/12-backtest.md).

Prinsip:
- TIDAK ada logika sinyal duplikat: replay memakai AnalysisEngine + evaluate_for_signal
  yang sama persis dengan produksi, lewat HistoricalProvider yang memotong data pada cutoff.
- Simulasi outcome PESIMIS: bila SL dan TP tersentuh di bar yang sama, dihitung SL.
- TP1 tercapai = exit penuh di TP1 (model single-exit, konservatif).
- Tidak pernah mengarang data; hasil = statistik historis, bukan janji masa depan.
"""
import math
from dataclasses import dataclass, field

from app.core.analysis.engine import ANALYSIS_TFS, AnalysisEngine
from app.core.market.provider import Candle, MarketDataProvider, validate
from app.core.signal.engine import evaluate_for_signal

FILL_WINDOW_BARS = 12  # setup expired bila entry tak tersentuh dalam N bar setelah sinyal


@dataclass(frozen=True)
class BacktestTrade:
    pair: str
    direction: str  # BUY | SELL
    signal_ts: int
    entry_ts: int | None
    exit_ts: int | None
    entry: float
    sl: float
    tp1: float
    tp2: float
    r: float | None  # None saat masih open / tidak fill
    outcome: str  # TP2 | TP1 | SL | EXPIRED | OPEN


@dataclass(frozen=True)
class BacktestSummary:
    total_signals: int
    filled: int
    wins: int
    losses: int
    open_: int
    win_rate_pct: float
    total_r: float
    profit_factor: float | None  # None bila tidak ada loss (tak terhingga)
    max_drawdown_r: float
    expectancy_r: float


@dataclass(frozen=True)
class BacktestResult:
    pair: str
    timeframe: str
    bars_tested: int
    evaluations: int = 0
    trades: list = field(default_factory=list)
    summary: BacktestSummary | None = None


def _r_multiple(direction: str, entry: float, sl: float, target: float) -> float:
    risk = abs(entry - sl)
    if risk == 0:
        return 0.0
    return round(abs(target - entry) / risk, 4)


def simulate_trade(direction: str, entry: float, sl: float, tp1: float, tp2: float,
                   future: list[Candle], *, pair: str = '', signal_ts: int = 0,
                   fill_window: int = FILL_WINDOW_BARS) -> BacktestTrade:
    """Simulasi satu setup ke depan.

    Fill: BUY terisi saat low <= entry (atau open <= entry = gap); SELL dicerminkan.
    Per bar setelah fill: SL dicek DULU (pesimis), lalu TP2, lalu TP1.
    """
    entry_ts: int | None = None
    start = -1
    for i, c in enumerate(future[:fill_window]):
        touched_entry = c.low <= entry <= c.high or (direction == "BUY" and c.open <= entry) \
            or (direction == "SELL" and c.open >= entry)
        if touched_entry:
            entry_ts = c.ts
            start = i
            break
    if entry_ts is None:
        return BacktestTrade(pair=pair, direction=direction, signal_ts=signal_ts, entry_ts=None,
                             exit_ts=None, entry=entry, sl=sl, tp1=tp1, tp2=tp2,
                             r=None, outcome="EXPIRED")

    r_tp1 = _r_multiple(direction, entry, sl, tp1)
    r_tp2 = _r_multiple(direction, entry, sl, tp2)
    for c in future[start:]:
        hit_sl = c.low <= sl if direction == "BUY" else c.high >= sl
        hit_tp2 = c.high >= tp2 if direction == "BUY" else c.low <= tp2
        hit_tp1 = c.high >= tp1 if direction == "BUY" else c.low <= tp1
        if hit_sl:
            return BacktestTrade(pair=pair, direction=direction, signal_ts=signal_ts, entry_ts=entry_ts,
                                 exit_ts=c.ts, entry=entry, sl=sl, tp1=tp1, tp2=tp2,
                                 r=-1.0, outcome="SL")
        if hit_tp2:
            return BacktestTrade(pair=pair, direction=direction, signal_ts=signal_ts, entry_ts=entry_ts,
                                 exit_ts=c.ts, entry=entry, sl=sl, tp1=tp1, tp2=tp2,
                                 r=r_tp2, outcome="TP2")
        if hit_tp1:
            return BacktestTrade(pair=pair, direction=direction, signal_ts=signal_ts, entry_ts=entry_ts,
                                 exit_ts=c.ts, entry=entry, sl=sl, tp1=tp1, tp2=tp2,
                                 r=r_tp1, outcome="TP1")
    return BacktestTrade(pair=pair, direction=direction, signal_ts=signal_ts, entry_ts=entry_ts,
                         exit_ts=None, entry=entry, sl=sl, tp1=tp1, tp2=tp2,
                         r=None, outcome="OPEN")


def summarize(trades: list[BacktestTrade], *, total_signals: int) -> BacktestSummary:
    closed = [t for t in trades if t.r is not None]
    wins = [t for t in closed if t.r > 0]
    losses = [t for t in closed if t.r <= 0]
    open_ = len(trades) - len(closed)
    gross_win = sum(t.r for t in wins)
    gross_loss = abs(sum(t.r for t in losses))
    total_r = round(gross_win - gross_loss, 2)

    # max drawdown pada kurva kumulatif R (urut waktu exit)
    curve, peak, dd = 0.0, 0.0, 0.0
    for t in sorted((x for x in closed if x.exit_ts is not None), key=lambda x: x.exit_ts):
        curve += t.r
        peak = max(peak, curve)
        dd = max(dd, peak - curve)

    n_closed = len(wins) + len(losses)
    return BacktestSummary(
        total_signals=total_signals,
        filled=len([t for t in trades if t.entry_ts is not None]),
        wins=len(wins), losses=len(losses), open_=open_,
        win_rate_pct=round(len(wins) / n_closed * 100, 1) if n_closed else 0.0,
        total_r=total_r,
        profit_factor=round(gross_win / gross_loss, 2) if gross_loss > 0 else (
            None if gross_win == 0 else math.inf),
        max_drawdown_r=round(dd, 2),
        expectancy_r=round(total_r / n_closed, 3) if n_closed else 0.0,
    )


class HistoricalProvider:
    """Provider dari snapshot data historis — slice semua TF pada cutoff yang sama."""

    name = "historical"

    def __init__(self, candles_by_tf: dict[str, list[Candle]]):
        missing = [tf for tf in ANALYSIS_TFS if tf not in candles_by_tf]
        if missing:
            raise ValueError(f"Snapshot backtest kurang timeframe: {', '.join(missing)}")
        self._data = {tf: sorted(candles, key=lambda c: c.ts) for tf, candles in candles_by_tf.items()}
        self.cutoff_ts = 0

    def set_cutoff(self, ts: int) -> None:
        self.cutoff_ts = ts

    async def get_candles(self, pair: str, timeframe: str, limit: int = 200) -> list[Candle]:
        validate(pair, timeframe)
        candles = [c for c in self._data[timeframe] if c.ts <= self.cutoff_ts]
        return candles[-limit:]


class BacktestEngine:
    """Replay historis memakai pipeline analisis + filter sinyal produksi."""

    def __init__(self, provider: MarketDataProvider | None = None):
        self.provider = provider

    async def run(self, pair: str, timeframe: str = "M15", *,
                  step_bars: int = 4, min_history: int = 150,
                  bars: int | None = None) -> BacktestResult:
        """Walk-forward replay.

        bars = jumlah candle TF dasar yang diambil untuk snapshot (None = default
        provider). Window yang dilihat engine analisis tetap <= 200 bar sebelum
        cutoff — sama persis dengan kondisi produksi.
        """
        validate(pair, timeframe)
        provider = self.provider or self._default_provider()
        snapshot: dict[str, list[Candle]] = {}
        for tf in ANALYSIS_TFS:
            snapshot[tf] = await provider.get_candles(pair, tf, limit=bars) if (
                tf == timeframe and bars) else await provider.get_candles(pair, tf)
        base = snapshot[timeframe]

        result = BacktestResult(pair=pair, timeframe=timeframe, bars_tested=len(base))
        if len(base) <= min_history:
            return result  # data kurang — jujur: tanpa evaluasi

        hist = HistoricalProvider(snapshot)
        engine = AnalysisEngine(hist)
        known_fingerprints: set[str] = set()
        trades: list[BacktestTrade] = []
        evaluations = 0

        i = min_history
        while i < len(base) - 1:
            hist.set_cutoff(base[i].ts)
            analysis = await engine.analyze(pair)
            evaluations += 1
            candidate = evaluate_for_signal(analysis)
            if candidate is not None and candidate.fingerprint not in known_fingerprints:
                known_fingerprints.add(candidate.fingerprint)
                trade = simulate_trade(
                    candidate.direction, candidate.entry, candidate.sl,
                    candidate.tp1, candidate.tp2, base[i + 1:],
                    pair=candidate.pair, signal_ts=base[i].ts,
                )
                trades.append(trade)
            i += step_bars

        from dataclasses import replace

        return replace(result, evaluations=evaluations, trades=trades,
                       summary=summarize(trades, total_signals=len(trades)))

    @staticmethod
    def _default_provider():
        from app.core.market.provider import get_provider

        return get_provider()
