"""AlphaVantageProvider — fallback market data live (§12).

Endpoint:
- FX_INTRADAY untuk M15/M30/H1 (interval 15min/30min/60min)
- FX_DAILY untuk D1
- H4 tidak ada endpoint native -> diagregasi jujur dari 4 candle H1
  (turunan data nyata, BUKAN angka karangan; didokumentasikan di §12)

Konversi JSON ke Candle:
- nilai OHLC bertipe string ("1. open") -> float
- urutan time series DESCENDING (terbaru dulu) -> dibalik ke ascending
- datetime "YYYY-MM-DD HH:MM:SS" -> unix epoch UTC
- forex tanpa volume -> default 0

Kegagalan jujur: retry singkat untuk 429/5xx dan Note/Information
(rate limit tier gratis), lalu raise ProviderError. Tidak pernah
mengarang data live.
"""
import asyncio
from datetime import datetime, timezone

from .provider import Candle, ProviderError, validate

_API_URL = "https://www.alphavantage.co/query"

_INTRADAY_INTERVAL = {"M15": "15min", "M30": "30min", "H1": "60min"}
_AGGREGATED_TF = "H4"  # dibangun dari H1

_RETRIES = 2
_RETRY_DELAYS = (2.0, 6.0)  # detik; tier gratis Alpha Vantage ~25 req/hari


def _to_symbols(pair: str) -> tuple[str, str]:
    """XAUUSD -> ("XAU", "USD")."""
    return pair[:-3], pair[-3:]


def _parse_ts(dt: str) -> int:
    return int(datetime.fromisoformat(dt).replace(tzinfo=timezone.utc).timestamp())


def _aggregate_h4(h1_candles: list[Candle]) -> list[Candle]:
    """Gabung tiap 4 candle H1 menjadi 1 candle H4 (open=first, close=last,
    high=max, low=min, volume=sum). Input WAJIB ascending."""
    out: list[Candle] = []
    for i in range(0, len(h1_candles) - 3, 4):
        chunk = h1_candles[i:i + 4]
        out.append(Candle(
            ts=chunk[0].ts,
            open=chunk[0].open,
            high=max(c.high for c in chunk),
            low=min(c.low for c in chunk),
            close=chunk[-1].close,
            volume=sum(c.volume for c in chunk),
        ))
    return out


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
        if timeframe == _AGGREGATED_TF:
            h1 = await self._fetch(pair, "H1", min(limit * 4, 400))
            return _aggregate_h4(h1)[-limit:]
        return await self._fetch(pair, timeframe, limit)

    async def _fetch(self, pair: str, timeframe: str, limit: int) -> list[Candle]:
        import httpx

        validate(pair, timeframe)
        from_symbol, to_symbol = _to_symbols(pair)
        if timeframe == "D1":
            params = {"function": "FX_DAILY", "from_symbol": from_symbol,
                      "to_symbol": to_symbol, "outputsize": "full", "apikey": self._api_key()}
            series_key = "Time Series FX (Daily)"
        else:
            params = {"function": "FX_INTRADAY", "from_symbol": from_symbol,
                      "to_symbol": to_symbol, "interval": _INTRADAY_INTERVAL[timeframe],
                      "outputsize": "full", "apikey": self._api_key()}
            series_key = f"Time Series FX ({_INTRADAY_INTERVAL[timeframe]})"

        last_error = ""
        for attempt in range(_RETRIES + 1):
            try:
                resp = await asyncio.to_thread(httpx.get, _API_URL, params=params, timeout=20.0)
                if resp.status_code == 429:
                    last_error = "rate limit Alpha Vantage (429)"
                elif resp.status_code >= 500:
                    last_error = f"Alpha Vantage server error ({resp.status_code})"
                elif resp.status_code != 200:
                    raise ProviderError(f"Alpha Vantage HTTP {resp.status_code}: {resp.text[:200]}")
                else:
                    data = resp.json()
                    # Error Message = invalid query (tidak perlu retry);
                    # Note/Information = rate limit / premium tier (coba lagi sekali).
                    if "Error Message" in data:
                        raise ProviderError(f"Alpha Vantage menolak: {data['Error Message'][:200]}")
                    if series_key not in data:
                        note = data.get("Note") or data.get("Information") or str(data)[:200]
                        last_error = f"Alpha Vantage menolak: {note}"
                    else:
                        series = data[series_key] or {}
                        candles = [
                            Candle(
                                ts=_parse_ts(dt),
                                open=float(v["1. open"]), high=float(v["2. high"]),
                                low=float(v["3. low"]), close=float(v["4. close"]),
                                volume=float(v.get("5. volume") or 0),
                            )
                            for dt, v in series.items()
                        ]
                        # descending (terbaru dulu) -> ascending sesuai kontrak provider
                        candles.sort(key=lambda c: c.ts)
                        return candles[-limit:]
            except httpx.HTTPError as e:
                last_error = f"network error: {e}"
            if attempt < _RETRIES:
                await asyncio.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])
        raise ProviderError(f"Gagal mengambil {pair} {timeframe} dari Alpha Vantage: {last_error}")

    @staticmethod
    def _api_key() -> str:
        from app.settings import get_settings

        return get_settings().alphavantage_api_key
