"""Test BacktestEngine (docs/12-backtest.md): simulasi outcome pesimis + walk-forward replay."""
import math
from datetime import datetime, timezone

import pytest

from app.core.backtest import (BacktestEngine, BacktestTrade, HistoricalProvider,
                               simulate_trade, summarize)
from app.core.analysis.engine import ANALYSIS_TFS
from app.core.market.provider import Candle


def _c(ts: int, o: float, h: float, lo: float, c: float) -> Candle:
    return Candle(ts=ts, open=o, high=h, low=lo, close=c, volume=1000)


# ---------------------------------------------------------------- simulate_trade

@pytest.mark.asyncio
async def test_buy_fills_and_exits_at_tp1():
    future = [
        _c(1, 99.9, 100.8, 99.5, 100.5),   # fill (low <= entry <= high), tanpa target
        _c(2, 100.6, 101.9, 100.2, 101.7),  # TP1 tersentuh
    ]
    t = simulate_trade("BUY", entry=100, sl=98, tp1=101.5, tp2=103, future=future)
    assert t.outcome == "TP1"
    assert t.r == pytest.approx(0.75)  # |tp1-entry| / risk(=2)
    assert t.exit_ts == 2


@pytest.mark.asyncio
async def test_sell_gap_open_fill_exits_at_sl():
    future = [
        _c(1, 101.5, 102.4, 100.9, 101.0),  # open >= entry -> fill gap
        _c(2, 101.2, 102.5, 100.8, 102.1),   # SL tersentuh (high >= sl)
    ]
    t = simulate_trade("SELL", entry=100, sl=102, tp1=98.5, tp2=97, future=future)
    assert t.entry_ts == 1
    assert t.outcome == "SL"
    assert t.r == -1.0


@pytest.mark.asyncio
async def test_same_bar_sl_and_tp_counts_as_sl_pesimis():
    future = [_c(1, 100, 102.0, 98.0, 100)]  # SL & TP di bar yang sama
    t = simulate_trade("BUY", entry=100, sl=99, tp1=101, tp2=102, future=future)
    assert t.outcome == "SL"
    assert t.r == -1.0


@pytest.mark.asyncio
async def test_entry_never_touched_expired():
    future = [_c(i, 101.5, 103, 101, 102) for i in range(20)]  # selalu di atas entry
    t = simulate_trade("BUY", entry=100, sl=98, tp1=101.5, tp2=103, future=future)
    assert t.outcome == "EXPIRED"
    assert t.entry_ts is None and t.r is None


@pytest.mark.asyncio
async def test_data_habis_sebelum_target_open():
    future = [_c(i, 100.2, 100.6, 99.9, 100.4) for i in range(30)]
    t = simulate_trade("BUY", entry=100, sl=95, tp1=105, tp2=110, future=future)
    assert t.outcome == "OPEN"


# ---------------------------------------------------------------- summarize

def test_summarize_metrics():
    mk = lambda **kw: BacktestTrade(pair="X", direction="BUY", signal_ts=0,
                                    entry_ts=1, exit_ts=2, entry=100, sl=98,
                                    tp1=101.5, tp2=103, **kw)
    trades = [
        mk(r=0.75, outcome="TP1"),
        mk(r=-1.0, outcome="SL"),
        mk(r=1.5, outcome="TP2"),
    ]
    s = summarize(trades, total_signals=4)  # 1 sinyal expired tidak masuk list trades
    assert (s.wins, s.losses, s.open_) == (2, 1, 0)
    assert s.win_rate_pct == 66.7
    assert s.total_r == pytest.approx(1.25)
    assert s.profit_factor == pytest.approx(2.25)
    # kurva R: +0.75 -> -0.25 -> +1.25 ; drawdown dari peak 0.75 ke -0.25 = 1.0
    assert s.max_drawdown_r == pytest.approx(1.0)
    assert s.expectancy_r == pytest.approx(0.417)  # dibulatkan 3 desimal di summarize


def test_summarize_no_losses_profit_factor_infinite():
    mk = lambda **kw: BacktestTrade(pair="X", direction="BUY", signal_ts=0,
                                    entry_ts=1, exit_ts=2, entry=100, sl=98,
                                    tp1=101.5, tp2=103, **kw)
    s = summarize([mk(r=0.75, outcome="TP1")], total_signals=1)
    assert s.profit_factor == math.inf  # tak pernah loss -> dirender "∞" di handler


def test_summarize_empty():
    s = summarize([], total_signals=0)
    assert s.win_rate_pct == 0.0 and s.total_r == 0.0


# ---------------------------------------------------------------- HistoricalProvider

def _snapshot(n: int = 10) -> dict:
    base_ts = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    out = {}
    for tf in ANALYSIS_TFS:
        out[tf] = [_c(base_ts + i * 900, 100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(n)]
    return out


@pytest.mark.asyncio
async def test_historical_provider_slices_on_cutoff():
    hp = HistoricalProvider(_snapshot())
    hp.set_cutoff(_snapshot()[ANALYSIS_TFS[0]][4].ts)
    candles = await hp.get_candles("XAUUSD", "M15")
    assert len(candles) == 5
    assert all(c.ts <= hp.cutoff_ts for c in candles)


@pytest.mark.asyncio
async def test_historical_provider_respects_limit():
    hp = HistoricalProvider(_snapshot())
    hp.set_cutoff(10**12)
    assert len(await hp.get_candles("XAUUSD", "M15", limit=3)) == 3


def test_historical_provider_requires_all_timeframes():
    with pytest.raises(ValueError):
        HistoricalProvider({"M15": []})


@pytest.mark.asyncio
async def test_historical_provider_rejects_invalid_tf():
    hp = HistoricalProvider(_snapshot())
    with pytest.raises(ValueError):
        await hp.get_candles("XAUUSD", "W1")


# ---------------------------------------------------------------- BacktestEngine.run

@pytest.mark.asyncio
async def test_engine_run_mock_produces_consistent_summary(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # jangan sentuh repo chart dir
    from app.core.market.mock import MockMarketDataProvider

    result = await BacktestEngine(MockMarketDataProvider()).run("XAUUSD", "M15")
    assert result.bars_tested > 0
    assert result.evaluations >= 1
    s = result.summary
    assert s is not None
    assert s.total_signals == len(result.trades)
    filled = sum(1 for t in result.trades if t.entry_ts is not None)
    assert s.filled == filled
    assert s.wins + s.losses + s.open_ == filled
    assert 0 <= s.win_rate_pct <= 100
    assert s.max_drawdown_r >= 0


@pytest.mark.asyncio
async def test_engine_run_bars_param_respected(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from app.core.market.mock import MockMarketDataProvider

    result = await BacktestEngine(MockMarketDataProvider()).run(
        "XAUUSD", "M15", bars=180, min_history=150)
    assert result.bars_tested == 180
    # i = 150,154,...,178 -> 8 evaluasi
    assert result.evaluations == 8


@pytest.mark.asyncio
async def test_engine_run_insufficient_data_returns_no_summary():
    class TinyProvider:
        name = "tiny"

        async def get_candles(self, pair, timeframe, limit=200):
            return _snapshot(20)[timeframe]

    result = await BacktestEngine(TinyProvider()).run("XAUUSD", "M15")
    assert result.summary is None
    assert result.evaluations == 0
