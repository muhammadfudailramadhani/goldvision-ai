"""Test market provider + analysis engine end-to-end dengan mock data (§12–§14)."""
import pytest

from app.core.analysis.engine import AnalysisEngine
from app.core.market.mock import MockMarketDataProvider
from app.core.market.provider import PAIRS, TIMEFRAMES, validate


@pytest.fixture()
def provider():
    return MockMarketDataProvider()


@pytest.mark.asyncio
async def test_mock_candles_shape(provider):
    candles = await provider.get_candles("XAUUSD", "M15", limit=200)
    assert len(candles) == 200
    assert all(c.high >= max(c.open, c.close) for c in candles)
    assert all(c.low <= min(c.open, c.close) for c in candles)
    assert all(c.ts < candles[i + 1].ts for i, c in enumerate(candles[:-1]))


@pytest.mark.asyncio
async def test_invalid_pair_rejected(provider):
    with pytest.raises(ValueError):
        await provider.get_candles("BTCUSD", "M15")
    with pytest.raises(ValueError):
        await provider.get_candles("XAUUSD", "M5")


def test_supported_pairs_and_tfs():
    assert "XAUUSD" in PAIRS and len(PAIRS) == 8
    assert TIMEFRAMES == ["M15", "M30", "H1", "H4", "D1"]


@pytest.mark.asyncio
async def test_analysis_full(provider):
    result = await AnalysisEngine(provider).analyze("XAUUSD")
    assert result.pair == "XAUUSD"
    assert 0 <= result.score.total <= 100
    assert result.recommendation.action in ("BUY", "SELL", "WAIT", "NO_TRADE")
    assert set(result.trend_by_tf) == {"D1", "H4", "H1", "M30", "M15"}
    # §15: skor dihitung dari komponen, total = jumlah subskor
    assert result.score.total == sum(c.score for c in result.score.components) or result.score.total == 100
    # §14: kalau BUY/SELL, tidak boleh tf_blocked
    if result.recommendation.action in ("BUY", "SELL"):
        assert not result.confluence.tf_blocked


@pytest.mark.asyncio
async def test_analysis_deterministic(provider):
    """Mock deterministik = dua run menghasilkan skor identik."""
    a = await AnalysisEngine(provider).analyze("EURUSD")
    b = await AnalysisEngine(provider).analyze("EURUSD")
    assert a.score.total == b.score.total
    assert a.recommendation.action == b.recommendation.action
