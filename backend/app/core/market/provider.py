"""Kontrak MarketDataProvider (§12) + factory berdasarkan MARKET_DATA_MODE."""
from dataclasses import dataclass
from typing import Protocol

TIMEFRAMES = ["M15", "M30", "H1", "H4", "D1"]
TF_MINUTES = {"M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}

# Pair internal memakai simbol tanpa slash; provider eksternal menangani format sendiri.
PAIRS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]


@dataclass(frozen=True)
class Candle:
    ts: int  # unix epoch seconds
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider(Protocol):
    name: str

    async def get_candles(self, pair: str, timeframe: str, limit: int = 200) -> list[Candle]:
        """Kembalikan candle terbaru (urut waktu naik). Raise ValueError untuk pair/TF invalid."""
        ...


class ProviderError(RuntimeError):
    pass


def validate(pair: str, timeframe: str) -> None:
    if pair not in PAIRS:
        raise ValueError(f"Pair tidak didukung: {pair}. Pilihan: {', '.join(PAIRS)}")
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Timeframe tidak didukung: {timeframe}. Pilihan: {', '.join(TIMEFRAMES)}")


def get_provider():
    """Factory sesuai settings.market_data_mode. Fallback ke mock bila provider asli belum dikonfigurasi (FASE 2)."""
    from app.settings import get_settings

    mode = get_settings().market_data_mode.lower()
    if mode == "mock":
        from .mock import MockMarketDataProvider

        return MockMarketDataProvider()
    if mode == "twelvedata":
        from .twelvedata import TwelveDataProvider

        return TwelveDataProvider()
    if mode == "alphavantage":
        from .alphavantage import AlphaVantageProvider

        return AlphaVantageProvider()
    if mode == "mt5":
        from .mt5 import MT5Provider

        return MT5Provider()
    raise ProviderError(f"MARKET_DATA_MODE tidak dikenal: {mode}")
