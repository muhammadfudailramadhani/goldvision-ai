"""MT5Provider — market data langsung dari terminal MetaTrader 5 (§12 alternatif gratis).

Paket `MetaTrader5` (pip) berbicara ke aplikasi terminal MT5 yang BERJALAN di
mesin yang sama. Konversi ndarray -> Candle:
- array sudah ASCENDING (terlama -> terbaru) — tidak perlu dibalik
- time = unix epoch detik (int64), OHLC = float64 native
- volume memakai tick_volume (real_volume sering 0 di forex)

Kegagalan jujur: terminal tidak menyala / symbol tidak ditemukan = ProviderError.
"""
from .provider import TIMEFRAMES, Candle, ProviderError, validate

# varian nama simbol umum di broker MT5 — dicoba berurutan
_SYMBOL_VARIANTS = {
    "XAUUSD": ["XAUUSD", "XAUUSD.a", "XAUUSD.raw", "GOLD", "GOLD.a"],
    "EURUSD": ["EURUSD", "EURUSD.a", "EURUSD.raw"],
    "GBPUSD": ["GBPUSD", "GBPUSD.a", "GBPUSD.raw"],
    "USDJPY": ["USDJPY", "USDJPY.a", "USDJPY.raw"],
    "USDCHF": ["USDCHF", "USDCHF.a", "USDCHF.raw"],
    "USDCAD": ["USDCAD", "USDCAD.a", "USDCAD.raw"],
    "AUDUSD": ["AUDUSD", "AUDUSD.a", "AUDUSD.raw"],
    "NZDUSD": ["NZDUSD", "NZDUSD.a", "NZDUSD.raw"],
}


class MT5Provider:
    name = "mt5"

    def __init__(self) -> None:
        import MetaTrader5 as mt5

        self._mt5 = mt5
        if not mt5.initialize():
            code = mt5.last_error()
            raise ProviderError(
                "MT5 initialize() gagal — pastikan terminal MetaTrader 5 "
                f"menyala & login di mesin ini. last_error={code}"
            )

    def _resolve_symbol(self, pair: str) -> str:
        """Cari varian nama simbol yang benar-benar ada di broker."""
        mt5 = self._mt5
        for candidate in _SYMBOL_VARIANTS.get(pair, [pair]):
            info = mt5.symbol_info(candidate)
            if info is not None:
                mt5.symbol_select(candidate, True)  # pastikan muncul di Market Watch
                return info.name
        raise ProviderError(
            f"Symbol {pair} tidak ditemukan di broker MT5 ini "
            f"(dicoba: {', '.join(_SYMBOL_VARIANTS.get(pair, [pair]))})"
        )

    async def get_candles(self, pair: str, timeframe: str, limit: int = 200) -> list[Candle]:
        import asyncio

        mt5 = self._mt5
        validate(pair, timeframe)
        tf_const = getattr(mt5, f"TIMEFRAME_{timeframe}")
        if timeframe not in TIMEFRAMES:  # pragma: no cover — dijaga validate()
            raise ValueError(timeframe)
        symbol = self._resolve_symbol(pair)
        # copy_rates_from_pos blocking — jalankan di thread agar event loop tidak macet
        rates = await asyncio.to_thread(
            mt5.copy_rates_from_pos, symbol, tf_const, 0, limit
        )
        if rates is None or len(rates) == 0:
            raise ProviderError(f"copy_rates_from_pos {symbol} {timeframe} kosong: {mt5.last_error()}")
        return [
            Candle(ts=int(r["time"]), open=float(r["open"]), high=float(r["high"]),
                   low=float(r["low"]), close=float(r["close"]),
                   volume=float(r["tick_volume"]))
            for r in rates
        ]
