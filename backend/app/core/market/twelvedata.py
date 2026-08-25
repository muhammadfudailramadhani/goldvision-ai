"""TwelveDataProvider — primary market data live (§12).

GET https://api.twelvedata.com/time_series — konversi JSON ke Candle:
- nilai OHLC bertipe string -> float
- urutan values DESCENDING (terbaru dulu) -> dibalik ke ascending
- datetime "YYYY-MM-DD HH:MM:SS" -> unix epoch (timezone param di-set UTC eksplisit)
- forex sering tanpa volume -> default 0

Kegagalan jujur: retry singkat untuk 429/5xx, lalu raise ProviderError.
Tidak pernah mengarang data live.
"""
import asyncio
from datetime import datetime, timezone

from .provider import Candle, ProviderError, validate

_API_URL = "https://api.twelvedata.com/time_series"

# interval internal -> format Twelve Data
_INTERVAL = {"M15": "15min", "M30": "30min", "H1": "1h", "H4": "4h", "D1": "1day"}

_RETRIES = 2
_RETRY_DELAYS = (1.0, 3.0)  # detik; Twelve Data 8 req/min pada tier gratis


def _to_symbol(pair: str) -> str:
    """XAUUSD -> XAU/USD (slash sebelum 3 huruf quote terakhir)."""
    return f"{pair[:-3]}/{pair[-3:]}"


def _parse_ts(dt: str) -> int:
    return int(datetime.fromisoformat(dt).replace(tzinfo=timezone.utc).timestamp())


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
        import httpx

        validate(pair, timeframe)
        params = {
            "symbol": _to_symbol(pair),
            "interval": _INTERVAL[timeframe],
            "outputsize": limit,
            "timezone": "UTC",
            "apikey": self._api_key(),
        }

        last_error = ""
        for attempt in range(_RETRIES + 1):
            try:
                resp = await asyncio.to_thread(
                    httpx.get, _API_URL, params=params, timeout=15.0
                )
                if resp.status_code == 429:
                    last_error = "rate limit Twelve Data (429)"
                elif resp.status_code >= 500:
                    last_error = f"Twelve Data server error ({resp.status_code})"
                elif resp.status_code != 200:
                    raise ProviderError(f"Twelve Data HTTP {resp.status_code}: {resp.text[:200]}")
                else:
                    data = resp.json()
                    if data.get("status") != "ok" or "values" not in data:
                        # code 404 pair tidak dikenal dsb. — tidak perlu retry
                        raise ProviderError(f"Twelve Data menolak: {data.get('message', str(data)[:200])}")
                    values = data["values"] or []
                    # descending (terbaru dulu) -> ascending sesuai kontrak provider
                    values.reverse()
                    return [
                        Candle(
                            ts=_parse_ts(v["datetime"]),
                            open=float(v["open"]), high=float(v["high"]),
                            low=float(v["low"]), close=float(v["close"]),
                            volume=float(v.get("volume") or 0),
                        )
                        for v in values
                    ]
            except httpx.HTTPError as e:
                last_error = f"network error: {e}"
            if attempt < _RETRIES:
                await asyncio.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])
        raise ProviderError(f"Gagal mengambil {pair} {timeframe} dari Twelve Data: {last_error}")

    @staticmethod
    def _api_key() -> str:
        from app.settings import get_settings

        return get_settings().twelvedata_api_key
