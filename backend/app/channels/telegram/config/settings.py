"""Telegram settings — aturan konfigurasi, BUKAN credentials (§7)."""

# Limits turunan dari Telegram Bot API & FAQ (§22)
MAX_PER_CHAT_PER_SEC = 1
MAX_GROUP_PER_MIN = 20
MAX_BULK_PER_SEC = 30

# Bot behavior
BOT_COMMANDS = ["/start", "/menu", "/analyze", "/signals", "/scanner",
             "/pnl", "/limit", "/status", "/subscribe", "/help"]

ADMIN_COMMANDS = ["/admin", "/admin_stats", "/admin_users", "/admin_signals",
                 "/admin_broadcast", "/admin_pnl", "/admin_vip", "/admin_limits"]

# Natural language intents yang memicu live analysis
ANALYSIS_KEYWORDS = ["analisa", "analisis", "analysis", "chart", "xauusd", "gold",
                     "emas", "eurusd", "gbpusd", "usdjpy", "bagaimana", "setup"]
