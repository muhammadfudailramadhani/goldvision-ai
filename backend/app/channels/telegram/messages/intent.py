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
    "/referral": "REFERRAL", "/stop": "STOP", "/backtest": "BACKTEST",
}

ANALYSIS_WORDS = re.compile(r"\b(analisa|analisis|analysis|analyze|chart|bagaimana|gimana|setup|sekarang)\b", re.I)
SIGNAL_WORDS = re.compile(r"\b(sinyal|signal)\b", re.I)
SCANNER_WORDS = re.compile(r"\b(scanner|scan|cari|best|terbaik)\b", re.I)
PNL_WORDS = re.compile(r"\b(pnl|profit|loss|hasil|minggu)\b", re.I)
BACKTEST_WORDS = re.compile(r"\b(backtest|back test|uji historis|replay)\b", re.I)
LIMIT_WORDS = re.compile(r"\b(limit|kuota|quota|sisa)\b", re.I)
HELP_WORDS = re.compile(r"\b(help|bantuan|cara|command)\b", re.I)
SUBSCRIBE_WORDS = re.compile(r"\b(subscribe|langganan|vip|upgrade)\b", re.I)


@dataclass(frozen=True)
class Intent:
    kind: str  # START|MENU|LIVE_ANALYSIS|SIGNALS|SCANNER|PNL|BACKTEST|LIMIT|STATUS|SUBSCRIBE|HELP|NOTIFICATIONS|REFERRAL|STOP|UNKNOWN
    pair: str | None = None
    is_command: bool = False
    referral_code: str | None = None  # payload /start <code> deep-link


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
        return Intent(kind, pair, is_command=True, referral_code=code)

    pair = _match_pair(lower)
    # Scanner/sinyal/backtest dicek SEBELUM analysis — "cari setup terbaik" bukan minta chart pair
    if SCANNER_WORDS.search(lower):
        return Intent("SCANNER", pair)
    if SIGNAL_WORDS.search(lower):
        return Intent("SIGNALS", pair)
    if BACKTEST_WORDS.search(lower):
        return Intent("BACKTEST", pair)
    if ANALYSIS_WORDS.search(lower) or (pair and not any(
            p.search(lower) for p in (PNL_WORDS, LIMIT_WORDS,
                                      HELP_WORDS, SUBSCRIBE_WORDS))):
        return Intent("LIVE_ANALYSIS", pair or "XAUUSD")
    if PNL_WORDS.search(lower):
        return Intent("PNL")
    if LIMIT_WORDS.search(lower):
        return Intent("LIMIT")
    if SUBSCRIBE_WORDS.search(lower):
        return Intent("SUBSCRIBE")
    if HELP_WORDS.search(lower):
        return Intent("HELP")
    if pair:  # cuma sebut pair -> anggap minta analysis
        return Intent("LIVE_ANALYSIS", pair)
    return Intent("UNKNOWN")
