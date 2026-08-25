"""Test AlphaVantageProvider — parsing FX_INTRADAY/FX_DAILY, agregasi H4, kegagalan jujur."""
import httpx
import pytest

from app.core.market.provider import ProviderError

MODULE = "app.core.market.alphavantage"


def _patch_settings(monkeypatch, key="test-key"):
    from types import SimpleNamespace

    monkeypatch.setattr("app.settings.get_settings",
                        lambda: SimpleNamespace(alphavantage_api_key=key))


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


INTRADAY_PAYLOAD = {
    "Meta Data": {"1. Information": "FX Intraday"},
    "Time Series FX (15min)": {
        "2026-01-02 00:15:00": {"1. open": "1.1010", "2. high": "1.1020",
                                "3. low": "1.1005", "4. close": "1.1018"},
        "2026-01-02 00:00:00": {"1. open": "1.1000", "2. high": "1.1012",
                                "3. low": "1.0995", "4. close": "1.1009"},
    },
}


@pytest.mark.asyncio
async def test_missing_api_key_raises(monkeypatch):
    _patch_settings(monkeypatch, key="")
    from app.core.market.alphavantage import AlphaVantageProvider

    with pytest.raises(ProviderError, match="ALPHAVANTAGE_API_KEY"):
        AlphaVantageProvider()


@pytest.mark.asyncio
async def test_intraday_parsed_ascending_floats(monkeypatch):
    _patch_settings(monkeypatch)
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append((url, params))
        return _FakeResponse(INTRADAY_PAYLOAD)

    monkeypatch.setattr(httpx, "get", fake_get)
    from app.core.market.alphavantage import AlphaVantageProvider

    candles = await AlphaVantageProvider().get_candles("EURUSD", "M15")
    assert len(candles) == 2
    assert [c.ts for c in candles] == sorted(c.ts for c in candles)  # ascending
    first = candles[0]
    assert (first.open, first.high, first.low, first.close) == (1.1000, 1.1012, 1.0995, 1.1009)
    url, params = calls[0]
    assert url.endswith("/query") and params["function"] == "FX_INTRADAY"
    assert params["interval"] == "15min"
    assert params["from_symbol"] == "EUR" and params["to_symbol"] == "USD"


@pytest.mark.asyncio
async def test_h4_aggregated_from_h1(monkeypatch):
    _patch_settings(monkeypatch)
    h1_payload = {
        "Time Series FX (60min)": {
            f"2026-01-01 0{h}:00:00": {
                "1. open": str(100 + h), "2. high": str(101 + h),
                "3. low": str(99 + h), "4. close": str(100.5 + h),
            } for h in range(4)
        },
    }
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _FakeResponse(h1_payload))
    from app.core.market.alphavantage import AlphaVantageProvider, _aggregate_h4

    # unit langsung
    from app.core.market.provider import Candle

    chunk = [Candle(ts=i, open=100 + i, high=101 + i, low=99 + i, close=100.5 + i, volume=1)
             for i in range(4)]
    agg = _aggregate_h4(chunk)
    assert len(agg) == 1
    assert (agg[0].open, agg[0].high, agg[0].low, agg[0].close) == (100, 104, 99, 103.5)
    assert agg[0].volume == 4

    # via get_candles H4 -> memanggil H1 lalu agregasi
    candles = await AlphaVantageProvider().get_candles("EURUSD", "H4")
    assert len(candles) == 1
    assert candles[0].close == pytest.approx(103.5)


@pytest.mark.asyncio
async def test_error_message_raises_without_retry(monkeypatch):
    _patch_settings(monkeypatch)
    calls = []
    monkeypatch.setattr(httpx, "get",
                        lambda url, **kw: (calls.append(1),
                                           _FakeResponse({"Error Message": "invalid API call"}))[1])

    async def _no_sleep(_):
        return None

    monkeypatch.setattr(f"{MODULE}.asyncio.sleep", _no_sleep)
    from app.core.market.alphavantage import AlphaVantageProvider

    with pytest.raises(ProviderError, match="invalid API call"):
        await AlphaVantageProvider().get_candles("EURUSD", "M15")
    assert len(calls) == 1  # tidak retry untuk error permintaan


@pytest.mark.asyncio
async def test_rate_limit_note_retries_then_fails(monkeypatch):
    _patch_settings(monkeypatch)
    calls = []
    monkeypatch.setattr(httpx, "get",
                        lambda url, **kw: (calls.append(1),
                                           _FakeResponse({"Note": "rate limit"}))[1])

    async def _no_sleep(_):
        return None

    monkeypatch.setattr(f"{MODULE}.asyncio.sleep", _no_sleep)
    from app.core.market.alphavantage import AlphaVantageProvider

    with pytest.raises(ProviderError, match="rate limit"):
        await AlphaVantageProvider().get_candles("XAUUSD", "D1")
    assert len(calls) == 3  # initial + 2 retry


def test_h4_aggregation_edges():
    from app.core.market.alphavantage import _aggregate_h4
    from app.core.market.provider import Candle

    def h1(n):
        return [Candle(ts=i, open=100, high=101, low=99, close=100.5, volume=1) for i in range(n)]

    assert _aggregate_h4([]) == []          # kosong
    assert _aggregate_h4(h1(3)) == []        # sisa < 4 -> dibuang (jujur)
    assert len(_aggregate_h4(h1(4))) == 1    # tepat 1 blok
    assert len(_aggregate_h4(h1(6))) == 1    # 2 bar sisa dibuang
    assert len(_aggregate_h4(h1(8))) == 2


@pytest.mark.asyncio
async def test_invalid_timeframe_raises_value_error(monkeypatch):
    _patch_settings(monkeypatch)
    monkeypatch.setattr(httpx, "get", lambda url, **kw: (_ for _ in ()).throw(AssertionError("no http")))
    from app.core.market.alphavantage import AlphaVantageProvider

    with pytest.raises(ValueError):
        await AlphaVantageProvider().get_candles("EURUSD", "W1")
    with pytest.raises(ValueError):
        await AlphaVantageProvider().get_candles("DOGEUSD", "H4")
