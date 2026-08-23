"""Market data layer (§12): provider interchangeable, mock untuk localhost.

Twelve Data (primary) dan Alpha Vantage (fallback) adalah implementasi
FASE 2 — file ini menyimpan kontrak & mock yang berjalan penuh sekarang.
"""
from .provider import MarketDataProvider, get_provider  # noqa: F401
