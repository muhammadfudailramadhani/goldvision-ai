"""Intent parser — natural language WAJIB bekerja (§18) + command mapping."""
import re
from dataclasses import dataclass

# §9: contoh input natural language yang harus dipahami
PAIR_ALIASES = {
    "gold": "XAUUSD", "emas": "XAUUSD", "xauusd": "XAUUSD", "xau": "XAUUSD", "gold sekarang": "XAUUSD",
    "eurusd": "EURUSD", "euro": "EURUSD", "eur/usd": "EURUSD",
    "gbpusd": "GBPUSD", "pound": "GBPUSD", "cable": "GBPUSD",
    "usdjpy": "USDJPY", "yen": "USDJPY",
    "usdchf": "USDCHF", "swissy": "USDCHF",
    "usdcad": "USDCAD", "audusd": "AUDUSD", "aussie": "AUDUSD",
    "nzdusd": "NZDUSD", "kiwi": "NZDUSD",
}

COMMAND_MAP = {
    "/start": "START", "/menu": "MENU", "/analyze": "LIVE_ANALYSIS", "/signals": "SIGNALS",
    "/scanner": "SCANNER", "/pnl": "PNL", "/limit": "LIMIT", "/status": "STATUS",
    "/subscribe": "SUBSCRIBE", "/help": "HELP", "/notifications": "NOTIFICATIONS",
    "/referral": "REFERRAL", "/stop": "STOP", "/backtest": "BACKTEST", "/konten": "KONTEN",
}

ANALYSIS_WORDS = re.compile(r"\b(analisa|analisis|analysis|analyze|chart|bagaimana|gimana|setup|sekarang)\b", re.I)
SIGNAL_WORDS = re.compile(r"\b(sinyal|signal)\b", re.I)
SCANNER_WORDS = re.compile(r"\b(scanner|scan|cari|best|terbaik)\b", re.I)
PNL_WORDS = re.compile(r"\b(pnl|profit|loss|hasil|minggu)\b", re.I)
BACKTEST_WORDS = re.compile(r"\b(backtest|back test|uji historis|replay)\b", re.I)
KONTEN_WORDS = re.compile(r"\b(konten|content|buatkan (post|konten))\b", re.I)
INDICATOR_TOKENS = re.compile(
    r"\b(rsi|macd|ema|sma|bb|bollinger|stoch|stochastic|obv|atr|"
    r"semua indikator|all indicators|indikator lengkap)\b", re.I)
INDICATOR_ALIAS = {"bollinger": "bb", "stochastic": "stoch", "stoch": "stoch",
                   "semua indikator": "__all__", "all indicators": "__all__",
                   "indikator lengkap": "__all__"}
LIMIT_WORDS = re.compile(r"\b(limit|kuota|quota|sisa)\b", re.I)
HELP_WORDS = re.compile(r"\b(help|bantuan|cara|command)\b", re.I)
SUBSCRIBE_WORDS = re.compile(r"\b(subscribe|langganan|vip|upgrade)\b", re.I)


@dataclass(frozen=True)
class Intent:
    kind: str  # START|MENU|LIVE_ANALYSIS|SIGNALS|SCANNER|PNL|BACKTEST|LIMIT|STATUS|SUBSCRIBE|HELP|NOTIFICATIONS|REFERRAL|STOP|UNKNOWN
    pair: str | None = None
    is_command: bool = False
    referral_code: str | None = None  # payload /start <code> deep-link
    indicators: tuple[str, ...] = ()  # pilihan kategori indikator (rsi, macd, ...)


def _extract_indicators(text: str) -> tuple[str, ...]:
    """Ambil token indikator dari teks. '__all__' = seluruh katalog."""
    tokens = [m.group(0).lower() for m in INDICATOR_TOKENS.finditer(text)]
    mapped = [INDICATOR_ALIAS.get(t, t) for t in tokens]
    if "__all__" in mapped:
        return ("__all__",)
    seen: list[str] = []
    for m in mapped:
        if m not in seen:
            seen.append(m)
    return tuple(seen)


def _match_pair(text_lower: str) -> str | None:
    # cek alias panjang dulu supaya "gold sekarang" tidak berhenti di "gold"
    for alias in sorted(PAIR_ALIASES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", text_lower):
            return PAIR_ALIASES[alias]
    return None


def parse_intent(text: str) -> Intent:
    text = text.strip()
    lower = text.lower()

    if text.startswith("/"):
        base = lower.split("@")[0].split()[0]
        kind = COMMAND_MAP.get(base, "ADMIN" if base.startswith("/admin") else "UNKNOWN")
        pair = _match_pair(lower)
        code = None
        # /start <code> — deep-link referral dari tautan t.me/<bot>?start=KODE
        if base == "/start":
            parts = lower.split()
            if len(parts) > 1 and re.fullmatch(r"[a-z0-9]{6,12}", parts[1]):
                code = parts[1].upper()
        return Intent(kind, pair, is_command=True, referral_code=code,
                      indicators=_extract_indicators(text))

    pair = _match_pair(lower)
    indicators = _extract_indicators(text)
    # Scanner/sinyal/backtest dicek SEBELUM analysis — "cari setup terbaik" bukan minta chart pair
    if SCANNER_WORDS.search(lower):
        return Intent("SCANNER", pair, indicators=indicators)
    if SIGNAL_WORDS.search(lower):
        return Intent("SIGNALS", pair, indicators=indicators)
    if BACKTEST_WORDS.search(lower):
        return Intent("BACKTEST", pair, indicators=indicators)
    if KONTEN_WORDS.search(lower):
        return Intent("KONTEN", pair, indicators=indicators)
    if ANALYSIS_WORDS.search(lower) or (pair and not any(
            p.search(lower) for p in (PNL_WORDS, LIMIT_WORDS,
                                      HELP_WORDS, SUBSCRIBE_WORDS))) or indicators:
        return Intent("LIVE_ANALYSIS", pair or "XAUUSD", indicators=indicators)
    if PNL_WORDS.search(lower):
        return Intent("PNL")
    if LIMIT_WORDS.search(lower):
        return Intent("LIMIT")
    if SUBSCRIBE_WORDS.search(lower):
        return Intent("SUBSCRIBE")
    if HELP_WORDS.search(lower):
        return Intent("HELP")
    if pair:  # cuma sebut pair -> anggap minta analysis
        return Intent("LIVE_ANALYSIS", pair, indicators=indicators)
    return Intent("UNKNOWN")
