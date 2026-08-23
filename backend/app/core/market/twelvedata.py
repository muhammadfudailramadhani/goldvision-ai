"""TwelveDataProvider — FASE 2 (primary market data, §12).

TIDAK DIIMPLEMENTASIKAN DI FASE FOUNDATION. Alasannya eksplisit, bukan diam-diam:
endpoint live butuh TWELVEDATA_API_KEY dan kebijakan rate limit akun nyata.
Saat fase 2: implement get_candles dengan GET /time_series, mapping symbol
XAUUSD -> XAU/USD, retry+fallback ke AlphaVantageProvider sesuai §12.

Jangan pernah mengarang data live di sini — kalau API gagal, raise ProviderError.
"""
from .provider import Candle, ProviderError, validate


class TwelveDataProvider:
    name = "twelvedata"

    def __init__(self) -> None:
        from app.settings import get_settings

        if not get_settings().twelvedata_api_key:
            raise ProviderError(
                "TwelveDataProvider butuh TWELVEDATA_API_KEY. "
                "Setel MARKET_DATA_MODE=mock untuk development."
            )

    async def get_candles(self, pair: str, timeframe: str, limit: int = 200) -> list[Candle]:
        validate(pair, timeframe)
        raise ProviderError("TwelveDataProvider belum diimplementasikan (FASE 2) — lihat docstring modul.")
