"""MockMarketDataProvider — deterministic random-walk, seeded per (pair, timeframe, hari).

Deterministik = test bisa mengandalkan angka yang sama di setiap run.
Struktur pasar (trend/zigzag) disuntikkan supaya modul analisis punya struktur
nyata untuk dibaca, bukan noise murni.
"""
import math
from datetime import datetime, timezone

from .provider import TF_MINUTES, Candle, validate

_BASE_PRICE = {
    "XAUUSD": 2350.0, "EURUSD": 1.0850, "GBPUSD": 1.2700, "USDJPY": 157.20,
    "USDCHF": 0.8850, "USDCAD": 1.3700, "AUDUSD": 0.6650, "NZDUSD": 0.6050,
}
_PIP = {"XAUUSD": 0.5, "USDJPY": 0.05}  # skala volatilitas per pair


def _seed(pair: str, timeframe: str) -> int:
    day = datetime.now(timezone.utc).toordinal()
    return hash((pair, timeframe, day)) % (2**31)


class MockMarketDataProvider:
    name = "mock"

    async def get_candles(self, pair: str, timeframe: str, limit: int = 200) -> list[Candle]:
        validate(pair, timeframe)
        step = TF_MINUTES[timeframe] * 60
        now = int(datetime.now(timezone.utc).timestamp())
        start = now - step * limit
        seed = _seed(pair, timeframe)
        base = _BASE_PRICE[pair] * (1 + ((seed % 100) - 50) / 500)  # variasi harian kecil
        unit = _PIP.get(pair, 0.0008) * 10

        candles: list[Candle] = []
        price = base
        # Fase trend: 4 segmen zigzag (turun-naik-turun-naik atau kebalikannya) supaya
        # ada swing high/low, structure, S/R, dan zone yang bisa dideteksi.
        seg = max(limit // 4, 8)
        up_first = (seed % 2) == 0
        for i in range(limit):
            phase = (i // seg) % 2
            drift = 1 if (phase == 0) == up_first else -1
            wave = math.sin(seed % 97 + i * 0.35) * unit  # gelombang intra-segmen
            move = drift * unit * 0.35 + wave * 0.4
            open_ = price
            close = max(round(open_ + move, 5), unit)
            spread = abs(move) + unit * (0.5 + abs(math.cos(i * 0.7 + seed % 13)))
            high = round(max(open_, close) + spread * 0.6, 5)
            low = round(max(min(open_, close) - spread * 0.6, 0.0001), 5)
            candles.append(
                Candle(ts=start + i * step, open=round(open_, 5), high=high, low=low,
                       close=round(close, 5), volume=float(1000 + (i * 37 + seed) % 900))
            )
            price = close
        return candles
