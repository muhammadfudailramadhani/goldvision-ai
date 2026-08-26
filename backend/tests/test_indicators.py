"""Test indikator teknikal + pemilihan kategori via intent + chart multi-panel."""
import pytest

from app.core.analysis.indicators import (INDICATOR_CATALOG, IndicatorSeries,
                                          bollinger, compute, macd, normalize_selection,
                                          obv, rsi, stochastic, summarize)
from app.core.market.provider import Candle


def _up_candles(n=80, base=100.0, step=0.6):
    return [Candle(ts=i * 900, open=base + i * step, high=base + i * step + 0.4,
                   low=base + i * step - 0.4, close=base + i * step + 0.2,
                   volume=100 + i)
            for i in range(n)]


def _flat_candles(n=60):
    return [Candle(ts=i * 900, open=100, high=100.1, low=99.9, close=100, volume=50)
            for i in range(n)]


# ---------------------------------------------------------------- matematika

def test_rsi_pure_uptrend_is_100_and_bounds():
    vals = rsi([100 + i for i in range(60)])
    assert vals[-1] == 100.0
    assert all(v is None or 0 <= v <= 100 for v in vals)


def test_rsi_flat_series_is_neutral_50():
    vals = rsi([100.0] * 40)
    assert vals[-1] == 50.0  # tidak ada gain/loss = netral, bukan 100


def test_rsi_pure_downtrend_is_0():
    vals = rsi([100 - i for i in range(60)])
    assert vals[-1] == 0.0


def test_macd_positive_in_uptrend_and_series_lengths_match():
    closes = [100 + i * 0.8 for i in range(80)]
    line, sig, hist = macd(closes)
    assert len(line) == len(sig) == len(hist) == 80
    assert line[-1] > 0 and hist[-1] is not None


def test_bollinger_contains_price_and_ordered():
    closes = [100 + (i % 7) * 0.5 for i in range(60)]
    mid, up, lo = bollinger(closes)
    assert up[-1] > mid[-1] > lo[-1]


def test_stochastic_bounds_and_obv_direction():
    candles = _up_candles()
    k, d = stochastic(candles)
    assert all(v is None or 0 <= v <= 100 for v in k)
    o = obv(candles)
    assert o[-1] > o[0]  # uptrend + volume positif -> OBV naik


# ---------------------------------------------------------------- katalog & seleksi

def test_normalize_selection_order_and_all():
    assert normalize_selection(["macd", "rsi"]) == ["rsi", "macd"]  # urut katalog
    assert normalize_selection(["bollinger"]) == ["bb"]
    full = normalize_selection(["semua indikator"])
    assert full == list(INDICATOR_CATALOG)
    assert normalize_selection(["rsi", "ngasal"]) == ["rsi"]  # asing diabaikan


def test_compute_returns_series_with_none_padding():
    candles = _up_candles()
    out = compute(candles, ["rsi", "macd"])
    keys = [s.key for s in out]
    assert keys == ["rsi", "macd"]
    r = out[0].series["RSI"]
    assert r[:14] == [None] * 14 and r[-1] is not None  # jujur: awal = None
    assert all(s.kind == "panel" for s in out)


def test_summarize_block_format():
    candles = _up_candles()
    block = summarize(compute(candles, ["rsi", "ema"]))
    assert "Indikator" in block and "RSI 14" in block
    assert "bukan saran" in block
    assert summarize([]) == ""


# ---------------------------------------------------------------- intent kategori

def test_intent_extracts_indicator_selection():
    from app.channels.telegram.messages.intent import parse_intent

    i1 = parse_intent("analisa gold dengan rsi macd")
    assert i1.kind == "LIVE_ANALYSIS" and i1.pair == "XAUUSD"
    assert set(i1.indicators) == {"rsi", "macd"}

    i2 = parse_intent("/analyze eurusd ema bollinger")
    assert i2.indicators == ("ema", "bb")

    i3 = parse_intent("gold semua indikator")
    assert i3.indicators == ("__all__",)

    i4 = parse_intent("Gold sekarang bagaimana?")
    assert i4.indicators == ()  # tanpa sebutan indikator = kosong


# ---------------------------------------------------------------- chart multi-panel

@pytest.mark.asyncio
async def test_chart_renders_indicator_panels(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.core.chart.generator import render_chart

    candles = _up_candles(120)
    series = compute(candles, ["ema", "bb", "rsi", "macd", "stoch"])
    path = render_chart(pair="XAUUSD", timeframe="M15", candles=candles,
                        indicators=series)
    assert path.exists()
    assert path.stat().st_size > 40_000  # 1 chart utama + 3 panel


@pytest.mark.asyncio
async def test_handler_analysis_with_indicators(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import importlib
    import sqlalchemy

    from app import db as db_mod

    engine = sqlalchemy.create_engine(
        f"sqlite:///{tmp_path / 't.db'}", connect_args={"check_same_thread": False})
    SF = sqlalchemy.orm.sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "SessionLocal", SF)
    for modname in ["app.channels.telegram.compliance.consent",
                    "app.channels.telegram.handlers.handler"]:
        mod = importlib.import_module(modname)
        if hasattr(mod, "SessionLocal"):
            monkeypatch.setattr(mod, "SessionLocal", SF)
    db_mod.init_db()

    from app.channels.base import MessageContext
    from app.channels.telegram.handlers.handler import TelegramHandler

    h = TelegramHandler()
    await h.handle(MessageContext("u-ind", "telegram", "0", "/start", "u-ind"))
    r = await h.handle(MessageContext("u-ind", "telegram", "1",
                                      "analisa gold dengan rsi macd", "u-ind"))
    assert r.intent == "LIVE_ANALYSIS"
    assert "Indikator" in r.reply and "RSI 14" in r.reply and "MACD" in r.reply
    assert r.chart_path  # chart dengan panel tetap ter-generate
