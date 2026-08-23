"""AlphaVantageProvider — FASE 2 (fallback market data, §12).

TIDAK DIIMPLEMENTASIKAN DI FASE FOUNDATION. Sama seperti TwelveDataProvider:
butuh ALPHAVANTAGE_API_KEY dan dipakai sebagai fallback ketika primary gagal.
Saat fase 2: implement FX_DAILY / REALTIME + retry, dan jangan pernah
mengarang angka — kegagalan = raise ProviderError supaya layer pemanggil
bisa fallback atau menolak analysis dengan jujur.
"""
from .provider import Candle, ProviderError, validate


class AlphaVantageProvider:
    name = "alphavantage"

    def __init__(self) -> None:
        from app.settings import get_settings

        if not get_settings().alphavantage_api_key:
            raise ProviderError(
                "AlphaVantageProvider butuh ALPHAVANTAGE_API_KEY. "
                "Setel MARKET_DATA_MODE=mock untuk development."
            )

    async def get_candles(self, pair: str, timeframe: str, limit: int = 200) -> list[Candle]:
        validate(pair, timeframe)
        raise ProviderError("AlphaVantageProvider belum diimplementasikan (FASE 2) — lihat docstring modul.")
